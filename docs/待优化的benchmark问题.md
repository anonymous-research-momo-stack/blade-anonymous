下面这些可能不是误报，但是benchmark中没有清晰的标注出来。所以需要优化benchmark.


## 🟢 高度可能不是误报（ground truth标记不完整）

### 大型运行时/工具的已知依赖
```
node: ['openssl', 'V8', 'zlib', 'libuv', 'c-ares', 'nghttp2', 'llhttp', 'Brotli', 'ICU', 'ngtcp2']
cmake: ['openssl', 'zlib', 'libcurl', 'bzip2', 'zstd']
upx: ['zlib']
```

### 数学/科学计算库的经典依赖
```
libosqp.so: ['SuiteSparse', 'QDLDL']
libgtsam.so: ['SuiteSparse', 'Eigen']
libcmaes.so: ['Eigen']
```

### C++库的Boost依赖（极常见）
```
libcpprest.so: ['Boost', 'WebSocket++']
libquickfast.so: ['Boost']
libazurestorage.so: ['cpprestsdk', 'Boost']
libInfluxDB.so: ['Boost']
libwt.so: ['Boost']
libmailio.so: ['Boost']
```

### Rust项目的crate依赖
```
libwasmtime.so: ['zstd', 'miniz_oxide', 'rayon', 'bumpalo', 'addr2line']
```

## 🟡 中等可能不是误报

### Protocol Buffers生态系统
```
libgoogle_api_client_proto.so: ['protobuf']
libetcd-cpp-api.so: ['protobuf', 'grpc']
libgrpc.so: ['Google Protobuf', 'OpenCensus', 'protoc-gen-validate', 'xDS (Envoy xDS APIs)', 'Google APIs (Protobuf Definitions)', 'Protocol Buffers Validation (protoc-gen-validate)', 'UDPA (Universal Data Plane API)']
libnlohmann_json_schema_validator.so: ['nlohmann_json', 'nlohmann/json']
```

### 工具库的实用依赖
```
libsixel.so: ['stb']
libvault.so: ['nlohmann_json']
libiowow.so: ['utf8proc']
libsymengine.so: ['cereal']
liblsl.so: ['loguru']
libsolace.so: ['murmur3']
```

### Tree-sitter语言绑定
```
libtree-sitter-cpp.so: ['tree-sitter']
libtree-sitter-c.so: ['tree-sitter']
```

### DNS/网络库依赖
```
libohNet.so: ['mdnsresponder']
libgetdns.so: ['ldns']
libspatialite.so: ['proj']
```

### WebSocket相关库
```
libfoxglove_websocket.so: ['WebSocket++', 'Asio', 'websocketpp']
```

### 数据库客户端依赖
```
objectbox-generator: ['flatbuffers']
```

### GNU工具的内部组件
```
m4: ['Gnulib', 'Getopt', 'gettext']
bison: ['obstack (GNU C Library component)', 'GNU obstack']
```

## 🟠 需要仔细验证

### 同项目不同组件
```
libopen62541pp.so: ['open62541']
libseasocks.so: ['md5']
libEdyn.so: ['entt']
crunch: ['crnlib']
libthrax.so: ['openfst', 'OpenGrm Thrax']
```

### 编译器工具链
```
gfortran: ['GCC']
x86_64-w64-mingw32-gcc-10.5.0: ['gfortran', 'GCC']
genie: ['premake', 'lua']
gn: ['abseil']
```

### 可能的header-only或模板库
```
libydcpp-tcpcat.so: ['asio', 'Asio']
```

## 🔴 可能确实是误报

### 版本/实现识别错误
```
libssl.so.56.0.0: ['openssl'] (ground truth: libressl)
libssl.so.52.0.0: ['openssl'] (ground truth: libressl)
clp: ['coin-utils'] (ground truth: coin-clp)
```

### 完全不同的库
```
libPcap++.so: ['LightPcapNg'] (已知不同项目)
libtree-sitter-cql.so: ['tree-sitter'] (已知应该分开)
libco.so: ['libco'] (ground truth: cocoyaxi，已知不同项目)
sqlite3: ['sqlcipher'] (不同的加密版本)
```

### Azure SDK语言版本混淆
```
libazure-core.so: ['azure-sdk-for-c'] (ground truth: azure-sdk-for-cpp)
```

## 🔵 纯粹别名问题（ALIAS_DICT已处理）
```
libfdk-aac.so: ['fdk-aac']
libhdr_histogram.so: ['HdrHistogram_c']
libltdl.so: ['libltdl']
libantlr4-runtime.so: ['antlr4']
libmysqlclient.so: ['MySQL']
libpaho-mqtt3as.so: ['paho.mqtt.c']
taocpp-taopq: ['taocpp/taopq']
libpq.so: ['PostgreSQL']
libsystemd.so: ['systemd']
boostdep: ['Boost']
libxapian.so: ['Xapian']
libarm_compute.so: ['ComputeLibrary']
```

## 🟤 FFT相关（需要单独处理）
```
libfft.so: ['FFTS', 'ooura-fft', 'FFTW']
```

**建议验证顺序：**
1. 🟢 高度可能不是误报 → 优先验证，很可能需要更新ground truth
2. 🟡 中等可能不是误报 → 仔细调研每个库的依赖关系
3. 🟠 需要仔细验证 → 可能需要源码分析
4. 🔴 可能确实是误报 → 需要改进检测算法
5. 🔵 别名问题 → 已通过ALIAS_DICT处理

这样分类后，你可以按优先级逐个确认了。