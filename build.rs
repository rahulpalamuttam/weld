use std::env;
use std::process::Command;

fn main() {
    let project_dir = env::var("CARGO_MANIFEST_DIR").unwrap();

    
    println!("cargo:rustc-link-lib=cuda");

    // You still need to set LD_LIBRARY_PATH to point to here
    // so the nvvm library can be loaded dynamically.
    println!("cargo:rustc-link-search=/usr/local/cuda-8.0/nvvm/lib64");
    println!("cargo:rustc-link-lib=dylib=nvvm");
    
    let status = Command::new("make")
        .arg("clean")
        .arg("-C")
        .arg(format!("{}/weld_rt/cpp/", project_dir))
        .status()
        .unwrap();
    assert!(status.success());

    let status = Command::new("make")
        .arg("-C")
        .arg(format!("{}/weld_rt/cpp/", project_dir))
        .status()
        .unwrap();
    assert!(status.success());

    // Link C++ standard library and some Mac-specific libraries
    let target = env::var("TARGET").unwrap();
    if target == "x86_64-apple-darwin" {
        let libs = vec!["z", "c++"];
        for lib in libs {
            println!("cargo:rustc-link-lib={}", lib);
        }
    }
    println!("cargo:rustc-link-lib=dylib=stdc++");

    // Link the weldrt C++ library
    println!("cargo:rustc-link-lib=static=weldrt");
    println!("cargo:rustc-link-search=native={}/weld_rt/cpp", project_dir);

    //println!("cargo:rustc-link-lib=static=ptxgen");
    //println!("cargo:rustc-link-search=native=lfs/1/rahul/weld");
}
