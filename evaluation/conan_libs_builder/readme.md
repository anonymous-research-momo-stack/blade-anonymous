# Conan Cross-Compilation Setup Guide

This guide provides setup instructions for building C++ libraries with multiple architectures, compilers, and configurations using Conan 2.x.

## 1. System Requirements

### Hardware & OS
- **Operating System**: Ubuntu 22.04 LTS (recommended) or Ubuntu 20.04+
- **Architecture**: x86_64 processor
- **Memory**: At least 4GB RAM
- **Storage**: At least 10GB free disk space

## 2. Install Tools and Dependencies

### System Packages
```bash
sudo apt update
sudo apt install -y build-essential cmake git python3 python3-pip pkg-config
```

### Conan 2.x
```bash
pip3 install --user conan
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Compilers
```bash
# Install Clang
sudo apt install -y clang

# Install ARM cross-compilation toolchain
sudo apt install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
```

### Python Dependencies
```bash
pip3 install --user loguru pydantic-settings environs
```

## 3. Conan Configuration

### Create Default Profile
```bash
conan profile detect --force
```

### Create ARM Cross-Compilation Profile
```bash
mkdir -p ~/.conan2/profiles
cat > ~/.conan2/profiles/arm64-cross << 'EOF'
[settings]
arch=armv8
build_type=Release
compiler=gcc
compiler.cppstd=gnu17
compiler.libcxx=libstdc++11
compiler.version=11
os=Linux

[buildenv]
CC=aarch64-linux-gnu-gcc
CXX=aarch64-linux-gnu-g++
AR=aarch64-linux-gnu-ar
RANLIB=aarch64-linux-gnu-ranlib
STRIP=aarch64-linux-gnu-strip
EOF
```

## 4. Usage and Expected Results

### Running the Code
```bash
python conan_library_builder.py
```

### Generated Build Configurations
The script will compile libraries with the following variants:

| Configuration | Architecture | Compiler | Build Type | Link Type |
|---------------|--------------|----------|------------|-----------|
| baseline      | x86_64       | GCC 11   | Release    | Shared    |
| debug         | x86_64       | GCC 11   | Debug      | Shared    |
| static        | x86_64       | GCC 11   | Release    | Static    |
| clang         | x86_64       | Clang 14 | Release    | Shared    |
| armv8         | armv8        | GCC 11   | Release    | Shared    |

### Expected Output Structure
```
benchmark_data/
├── {library_name}/
│   └── {version}/
│       ├── {library}_{version}_baseline/
│       ├── {library}_{version}_debug/
│       ├── {library}_{version}_static/
│       ├── {library}_{version}_clang/
│       └── {library}_{version}_armv8/
```

Each configuration directory contains:
- Compiled binary files
- Header files
- Dependency libraries
- `metadata.json` with build information and dependency tree

### Success Indicators
When successful, you'll see output like:
```
✅ baseline 编译成功
✅ debug 编译成功  
✅ static 编译成功
✅ clang 编译成功
✅ armv8 编译成功
✅ OpenSSL库批量编译完成!
成功编译: 5 个配置
失败编译: 0 个配置
```

This setup enables comprehensive binary analysis across different compilation environments for software composition analysis (SCA) research.