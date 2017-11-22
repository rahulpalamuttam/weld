#include "runtime.h"
#include "assert.h"
#include <algorithm>

struct simple_dict {
  void *data;
  int64_t size;
  int64_t capacity;
  bool full; // only local dicts should be marked as full
};

struct weld_dict {
  void *dicts; // one dict per thread plus a global dict
  int32_t key_size;
  int32_t key_array_el_size;
  int32_t val_size;
  int32_t to_array_true_val_size; // might discard some trailing part of the value when
  // converting to array (useful for groupbuilder)
  int64_t max_local_bytes;
  // following two fields are used when finalizing dict (merging all locals into global)
  int32_t cur_local_dict;
  int64_t cur_slot_in_dict;
  bool finalized; // all keys have been moved to global
  pthread_mutex_t global_lock;
};

struct weld_arr {
  void *data;
  int64_t size;
};

inline int32_t slot_size(weld_dict *wd) {
  return sizeof(uint8_t) /* space for `filled` field */ + wd->key_size + wd->val_size +
    sizeof(int32_t) /* space for key hash */;
}

inline void *slot_at_with_data(int64_t slot_offset, weld_dict *wd, void *data) {
  return (void *)((uint8_t *)data + slot_offset * slot_size(wd));
}

inline void *slot_at(int64_t slot_offset, weld_dict *wd, simple_dict *sd) {
  return slot_at_with_data(slot_offset, wd, sd->data);
}

inline void *key_at(void *slot) {
  return (void *)((uint8_t *)slot + sizeof(uint8_t));
}

inline void *val_at(weld_dict *wd, void *slot) {
  return (void *)((uint8_t *)slot + sizeof(uint8_t) + wd->key_size);
}

inline int32_t *hash_at(weld_dict *wd, void *slot) {
  return (int32_t *)((uint8_t *)slot + sizeof(uint8_t) + wd->key_size + wd->val_size);
}

inline uint8_t *filled_at(void *slot) {
  return (uint8_t *)slot;
}

inline bool slot_in_local(weld_dict *wd, void *slot) {
  simple_dict *local = (simple_dict *)weld_rt_get_merger_at_index(wd->dicts, sizeof(simple_dict),
    weld_rt_thread_id());
  intptr_t slot_int = (intptr_t)slot;
  return slot_int >= (intptr_t)local->data &&
    slot_int < (intptr_t)((uint8_t *)local->data + slot_size(wd) * local->capacity);
}

inline bool should_resize_dict_at_size(int64_t size, simple_dict *sd) {
  // 70% full
  return size * 10 >= sd->capacity * 7;
}

inline simple_dict *get_dict_at_index(weld_dict *wd, int32_t i) {
  return (simple_dict *)weld_rt_get_merger_at_index(wd->dicts, sizeof(simple_dict), i);
}

inline simple_dict *get_local_dict(weld_dict *wd) {
  return get_dict_at_index(wd, weld_rt_thread_id());
}

inline simple_dict *get_global_dict(weld_dict *wd) {
  return get_dict_at_index(wd, weld_rt_get_nworkers());
}

extern "C" void *weld_rt_dict_new(int32_t key_size, int32_t key_array_el_size, int32_t val_size,
  int32_t to_array_true_val_size, int64_t max_local_bytes, int64_t capacity) {
  weld_dict *wd = (weld_dict *)weld_run_malloc(weld_rt_get_run_id(), sizeof(weld_dict));
  memset(wd, 0, sizeof(weld_dict));
  wd->key_size = key_size;
  wd->key_array_el_size = key_array_el_size;
  wd->val_size = val_size;
  wd->to_array_true_val_size = to_array_true_val_size;
  wd->max_local_bytes = max_local_bytes;
  wd->dicts = weld_rt_new_merger(sizeof(simple_dict), weld_rt_get_nworkers() + 1);
  for (int32_t i = 0; i < weld_rt_get_nworkers() + 1; i++) {
    simple_dict *d = get_dict_at_index(wd, i);
    d->size = 0;
    d->capacity = capacity;
    d->data = weld_run_malloc(weld_rt_get_run_id(), capacity * slot_size(wd));
    memset(d->data, 0, capacity * slot_size(wd));
  }
  pthread_mutex_init(&wd->global_lock, NULL);
  return (void *)wd;
}

inline bool keys_equal(weld_dict *wd, void *key1, void *key2) {
  if (wd->key_array_el_size != 0) {
    weld_arr *arr1 = (weld_arr *)key1;
    weld_arr *arr2 = (weld_arr *)key2;
    return arr1->size == arr2->size &&
      memcmp(arr1->data, arr2->data, arr1->size * wd->key_array_el_size) == 0;
  } else {
    return memcmp(key1, key2, wd->key_size) == 0;
  }
}

inline void *simple_dict_lookup(weld_dict *wd, simple_dict *sd, int32_t hash, void *key,
  bool collision_possible) {
  int64_t first_offset = hash % sd->capacity;
  for (int64_t i = 0; i < sd->capacity; i++) {
    // can do the bitwise and because capacity is always a power of two
    void *cur_slot = slot_at((first_offset + i) & (sd->capacity - 1), wd, sd);
    if (*filled_at(cur_slot)) {
      if (collision_possible && *hash_at(wd, cur_slot) == hash &&
        keys_equal(wd, key, key_at(cur_slot))) {
        return cur_slot;
      }
    } else {
      *hash_at(wd, cur_slot) = hash; // store hash here in case we end up filling this slot (no
      // problem if not)
      return cur_slot;
    }
  }
  // should never reach this
  assert(false);
  return NULL;
}

inline void resize_dict(weld_dict *wd, simple_dict *sd) {
  void *old_data = sd->data;
  int64_t old_capacity = sd->capacity;
  sd->capacity *= 2;
  sd->data = weld_run_malloc(weld_rt_get_run_id(), sd->capacity * slot_size(wd));
  memset(sd->data, 0, sd->capacity * slot_size(wd));
  for (int64_t i = 0; i < old_capacity; i++) {
    void *old_slot = slot_at_with_data(i, wd, old_data);
    if (*filled_at(old_slot)) {
      // will never compare the keys when collision_possible = false so can pass NULL
      void *new_slot = simple_dict_lookup(wd, sd, *hash_at(wd, old_slot), NULL, false);
      memcpy(new_slot, old_slot, slot_size(wd));
    }
  }
  weld_run_free(weld_rt_get_run_id(), old_data);
}

// Can only be doing a lookup to examine value if dict is already finalized. Otherwise must
// be for the purposes of merging.
extern "C" void *weld_rt_dict_lookup(void *d, int32_t hash, void *key) {
  weld_dict *wd = (weld_dict *)d;
  if (!wd->finalized) {
    simple_dict *sd = get_local_dict(wd);
    void *slot = simple_dict_lookup(wd, sd, hash, key, true);
    if (!sd->full || *filled_at(slot)) {
      return slot;
    }
  }
  if (!wd->finalized) {
    // take the lock since if we are not finalized, there are still writes going on
    pthread_mutex_lock(&wd->global_lock);
  }
  simple_dict *global = get_global_dict(wd);
  return simple_dict_lookup(wd, global, hash, key, true);
}

extern "C" void weld_rt_dict_put(void *d, void *slot) {
  weld_dict *wd = (weld_dict *)d;
  uint8_t old_filled = *filled_at(slot);
  if (!old_filled) {
    *filled_at(slot) = 1;
    if (slot_in_local(wd, slot)) {
      simple_dict *local = get_local_dict(wd);
      local->size++;
      if (should_resize_dict_at_size(local->size, local)) {
        resize_dict(wd, local);
      } else if (should_resize_dict_at_size(local->size + 1, local) &&
        local->capacity * 2 * slot_size(wd) > wd->max_local_bytes) {
        local->full = true;
      }
    } else {
      simple_dict *global = get_global_dict(wd);
      global->size++;
      if (should_resize_dict_at_size(global->size, global)) {
        resize_dict(wd, global);
      }
    }
  }
  if (!wd->finalized && !slot_in_local(wd, slot)) {
    pthread_mutex_unlock(&wd->global_lock);
  }
}

inline void advance_finalize_iterator(weld_dict *wd) {
  wd->cur_slot_in_dict++;
  if (wd->cur_slot_in_dict == get_dict_at_index(wd, wd->cur_local_dict)->capacity) {
    wd->cur_local_dict++;
    wd->cur_slot_in_dict = 0;
  }
}

extern "C" void *weld_rt_dict_finalize_next_local_slot(void *d) {
  weld_dict *wd = (weld_dict *)d;
  wd->finalized = true; // immediately mark as finalized ... we expect the client to keep
  // calling this method until it returns NULL, and only after this perform other operations
  // on the dictionary
  while (wd->cur_local_dict != weld_rt_get_nworkers()) {
    simple_dict *cur_dict = get_dict_at_index(wd, wd->cur_local_dict);
    void *next_slot = slot_at(wd->cur_slot_in_dict, wd, cur_dict);
    advance_finalize_iterator(wd);
    if (*filled_at(next_slot)) {
      return next_slot;
    }
  }
  return NULL;
}

extern "C" void *weld_rt_dict_finalize_global_slot_for_local(void *d, void *local_slot) {
  weld_dict *wd = (weld_dict *)d;
  return weld_rt_dict_lookup(wd, *hash_at(wd, local_slot), key_at(local_slot));
}

extern "C" void *weld_rt_dict_to_array(void *d, int32_t value_offset_in_struct, int32_t struct_size) {
  weld_dict *wd = (weld_dict *)d;
  int32_t post_key_padding = value_offset_in_struct - wd->key_size;
  assert(wd->finalized);
  simple_dict *global = get_global_dict(wd);
  void *array = weld_run_malloc(weld_rt_get_run_id(),
    global->size * struct_size);
  int64_t next_arr_slot = 0;
  for (int64_t i = 0; i < global->capacity; i++) {
    void *cur_slot = slot_at(i, wd, global);
    if (*filled_at(cur_slot)) {
      memcpy((uint8_t *)array + next_arr_slot * struct_size,
        key_at(cur_slot), wd->key_size);
      memcpy((uint8_t *)array + next_arr_slot * struct_size +
        wd->key_size + post_key_padding, val_at(wd, cur_slot), wd->to_array_true_val_size);
      next_arr_slot++;
    }
  }
  assert(next_arr_slot == global->size);
  return array;
}

extern "C" int64_t weld_rt_dict_get_size(void *d) {
  weld_dict *wd = (weld_dict *)d;
  assert(wd->finalized);
  return get_global_dict(wd)->size;
}

extern "C" void weld_rt_dict_free(void *d) {
  weld_dict *wd = (weld_dict *)d;
  for (int32_t i = 0; i < weld_rt_get_nworkers() + 1; i++) {
    simple_dict *d = get_dict_at_index(wd, i);
    weld_run_free(weld_rt_get_run_id(), d->data);
  }
  weld_rt_free_merger(wd->dicts);
  pthread_mutex_destroy(&wd->global_lock);
  weld_run_free(weld_rt_get_run_id(), wd);
}

/* GroupBuilder */

struct weld_arr_growable {
  weld_arr a;
  int64_t capacity;
};

struct weld_gb {
  void *wd;
  int32_t val_size;
};

extern "C" void *weld_rt_gb_new(int32_t key_size, int32_t key_array_el_size, int32_t val_size,
  int64_t max_local_bytes, int64_t capacity) {
  weld_gb *gb = (weld_gb *)weld_run_malloc(weld_rt_get_run_id(), sizeof(weld_gb));
  gb->wd = weld_rt_dict_new(key_size, key_array_el_size, sizeof(weld_arr_growable),
    sizeof(weld_arr), max_local_bytes, capacity);
  gb->val_size = val_size;
  return (void *)gb;
}

inline void resize_weld_arr(weld_gb *gb, weld_arr_growable *arr, int64_t new_cap) {
  void *old_data = arr->a.data;
  arr->a.data = weld_run_malloc(weld_rt_get_run_id(), new_cap * gb->val_size);
  memcpy(arr->a.data, old_data, arr->a.size * gb->val_size);
  arr->capacity = new_cap;
  weld_run_free(weld_rt_get_run_id(), old_data);
}

inline void *el_at(weld_gb *gb, weld_arr_growable *arr, int64_t i) {
  return (void *)((uint8_t *)arr->a.data + i * gb->val_size);
}

extern "C" void weld_rt_gb_merge(void *b, void *key, int32_t hash, void *value) {
  weld_gb *gb = (weld_gb *)b;
  void *slot = weld_rt_dict_lookup(gb->wd, hash, key);
  weld_dict *wd = (weld_dict *)gb->wd;
  weld_arr_growable *arr = (weld_arr_growable *)val_at(wd, slot);
  if (*filled_at(slot)) {
    if (arr->capacity == arr->a.size) {
      resize_weld_arr(gb, arr, arr->capacity * 2);
    }
  } else {
    arr->capacity = 16;
    arr->a.data = weld_run_malloc(weld_rt_get_run_id(), arr->capacity * gb->val_size);
    arr->a.size = 0;
    memcpy(key_at(slot), key, wd->key_size);
  }
  memcpy(el_at(gb, arr, arr->a.size), value, gb->val_size);
  arr->a.size++;
  weld_rt_dict_put(gb->wd, slot);
}

extern "C" void *weld_rt_gb_result(void *b) {
  weld_gb *gb = (weld_gb *)b;
  weld_dict *wd = (weld_dict *)gb->wd;
  void *local_slot;
  while ((local_slot = weld_rt_dict_finalize_next_local_slot(gb->wd)) != NULL) {
    weld_arr_growable *local_arr = (weld_arr_growable *)val_at(wd, local_slot);
    void *global_slot = weld_rt_dict_finalize_global_slot_for_local(gb->wd, local_slot);
    weld_arr_growable *global_arr = (weld_arr_growable *)val_at(wd, global_slot);
    if (*filled_at(global_slot)) {
      if (local_arr->a.size + global_arr->a.size > global_arr->capacity) {
        resize_weld_arr(gb, global_arr,
          std::max(global_arr->capacity * 2, local_arr->a.size + global_arr->a.size));
      }
    } else {
      global_arr->capacity = std::max((int64_t)16, local_arr->a.size);
      global_arr->a.data = weld_run_malloc(weld_rt_get_run_id(),
        global_arr->capacity * gb->val_size);
      global_arr->a.size = 0;
      memcpy(key_at(global_slot), key_at(local_slot), wd->key_size);
    }
    memcpy(el_at(gb, global_arr, global_arr->a.size), local_arr->a.data,
      gb->val_size * local_arr->a.size);
    global_arr->a.size += local_arr->a.size;
    weld_rt_dict_put(gb->wd, global_slot);
    weld_run_free(weld_rt_get_run_id(), local_arr->a.data);
  }
  return gb->wd;
}

extern "C" void weld_rt_gb_free(void *gb) {
  weld_run_free(weld_rt_get_run_id(), gb);
}