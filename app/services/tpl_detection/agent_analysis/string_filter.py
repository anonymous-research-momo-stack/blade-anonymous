import re
import subprocess
import traceback
from typing import List, Dict, Set
from collections import Counter
from loguru import logger

KNOWN_COMPONENTS = \
    ['7bitconf', 'access_private', '7zip', 'abseil', '7bitdi', 'acado', 'aggeom-agg', 'alpaca', 'andreasbuhr-cppcoro',
     'alembic', 'alac', 'amgcl', 'amqp-cpp', 'annoy', 'aeron', 'anyrpc', 'apriltag', 'any-lite', 'antlr4-cppruntime',
     'approvaltests.cpp', 'apr-util', 'arduinojson', 'aravis', 'arcus', 'argh', 'argparse', 'args-parser', 'argon2',
     'argz', 'argtable3', 'arsenalgear', 'artery-font-format', 'arg_router', 'asio', 'asio-grpc', 'asn1c', 'asmjit',
     'asmtk', 'astro-informatics-so3', 'asyncly', 'asyncpp', 'astc-codec', 'asyncplusplus', 'async_simple',
     'atomic_queue', 'audiofile', 'avir', 'avahi', 'avcpp', 'aws-c-cal', 'aws-c-common', 'aws-c-auth', 'audiowaveform',
     'aws-c-compression', 'aws-c-event-stream', 'aws-c-http', 'aws-c-mqtt', 'aws-c-s3', 'aws-c-io', 'aws-c-sdkutils',
     'aws-cdi-sdk', 'aws-checksums', 'aws-crt-cpp', 'aws-kvs-pic', 'aws-lambda-cpp', 'aws-libfabric', 'aws-sdk-cpp',
     'backport-cpp', 'backward-cpp', 'azure-storage-cpp', 'bacnet-stack', 'azure-sdk-for-cpp', 'bandit', 'base64',
     'battery-embed', 'bdwgc', 'bear', 'beauty', 'behaviortree.cpp', 'bezier', 'bertrand', 'bgfx', 'benchmark', 'bimg',
     'bitflags', 'bit-lite', 'bitmagic', 'bitserializer', 'bitsery', 'blend2d', 'boolinq', 'boolean-lite',
     'boost-ext-ut', 'boost', 'boost-leaf', 'box2d', 'botan', 'bredis', 'breakpad', 'brigand', 'brotli', 'brunsli',
     'btyacc', 'bshoshany-thread-pool', 'brynet', 'bullet3', 'bvdberg-ctest', 'butteraugli', 'byte-lite', 'bzip3',
     'c-blosc', 'c-ares', 'c-client', 'c-blosc2', 'c-dbg-macro', 'c4core', 'caches', 'cajun-jsonapi', 'canary',
     'canvas_ity', 'cargs', 'capstone', 'cassandra-cpp-driver', 'capnproto', 'cc65', 'ccache', 'cccl', 'cctag', 'cctz',
     'cd3-boost-unit-definitions', 'cereal', 'celero', 'certify', 'ceres-solver', 'cern-root', 'cgal', 'cgif',
     'cfgfile', 'cgltf', 'cglm', 'chaiscript', 'cgns', 'charls', 'choc', 'chunkio', 'cista', 'circularbuffer', 'cjson',
     'cityhash', 'civetweb', 'cimg', 'cli11', 'clipboard_lite', 'clickhouse-cpp', 'clipp', 'clara', 'clove-unit',
     'clipper2', 'cminpack', 'cn-cbor', 'cnats', 'cocoyaxi', 'cnpy', 'coin-cbc', 'coin-clp', 'coin-cgl', 'coin-osi',
     'coin-utils', 'commata', 'compute_library', 'concurrencpp', 'concurrentqueue', 'confu_json', 'console_bridge',
     'continuable', 'copypp', 'corrade', 'cose-c', 'coost', 'cotila', 'cpp-channel', 'cpp-dump', 'cpp-httplib',
     'cpp-ipc', 'cpp-jwt', 'cpp-smtpclient-library', 'cpp-optparse', 'cpp-validator', 'cpp-sort', 'cpp-taskflow',
     'cpp-yyjson', 'cpp-lazy', 'cppbenchmark', 'cppcheck', 'cppcmd', 'cppcodec', 'cppcommon', 'cppitertools',
     'cppfront', 'cppdap', 'cppkafka', 'cppserver', 'cpptoml', 'cpptrace', 'cpputest', 'cpp_project_framework',
     'cppzmq', 'cpprestsdk', 'cprocessing', 'cpuinfo', 'cqrlib', 'cpu_features', 'crc_cpp', 'crcpp', 'create-dmg',
     'crc32c', 'croncpp', 'crossdb', 'crossguid', 'crow', 'crunch', 'cryptopp', 'csvmonkey', 'cs_libguarded', 'cthash',
     'ctml', 'ctpg', 'ctrack', 'ctrl-c', 'cubicinterpolation', 'ctre', 'cuda-api-wrappers', 'cuda-kat', 'curlpp',
     'cuda-samples', 'cute_headers', 'cutlass', 'cvplot', 'cwalk', 'cxxgraph', 'cxxopts', 'cyclonedds-cxx',
     'cyrus-sasl', 'cyclonedds', 'czmq', 'dacap-clip', 'darknet', 'dataframe', 'daw_header_libraries', 'daw_json_link',
     'daw_utf_range', 'dbcppp', 'dbg-macro', 'dcmtk', 'debug_assert', 'dd-opentracing-cpp', 'decimal_for_cpp', 'deco',
     'detools', 'devil', 'dice-template-library', 'detours', 'diligent-core', 'diligent-fx', 'diligent-tools',
     'diligentgraphics-spirv-headers', 'diligentgraphics-spirv-tools', 'diligentgraphics-vulkan-headers', 'dime',
     'dirent', 'discount', 'dispenso', 'djinni-generator', 'directshowbaseclasses', 'djinni-support-lib',
     'directx-headers', 'dlib', 'dlpack', 'dnet', 'docopt.cpp', 'doxygen', 'double-conversion', 'djvulibre',
     'dragonbox', 'drflac', 'draco', 'drmp3', 'dr_libs', 'drwav', 'dsp-filters', 'duckx', 'duckdb', 'drogon', 'duktape',
     'dylib', 'eabase', 'eastl', 'earcut', 'easyexif', 'easylzma', 'easy_profiler', 'easyloggingpp', 'easyhttpcpp',
     'edlib', 'ecos', 'edyn', 'efsw', 'effcee', 'egl-headers', 'embedded_ringbuf_cpp', 'eiquadprog', 'elfio', 'embag',
     'effolkronium-random', 'emhash', 'emio', 'embree', 'enhex-generic_serialization', 'emsdk', 'enchant',
     'enhex-strong_type', 'enet', 'embree3', 'entityx', 'enkits', 'enum-flags', 'enumbitmask', 'erikzenker-hsm',
     'etc2comp', 'erkir', 'eternal', 'etcd-cpp-apiv3', 'ethash', 'eudev', 'eventpp', 'exiv2', 'expat', 'expected-lite',
     'exprtk', 'ezc3d', 'faac', 'evmc', 'faker-cxx', 'fakeit', 'farmhash', 'fast-cpp-csv-parser', 'fast-cdr',
     'fastgltf', 'fast-dds', 'fastnoise2', 'fastprng', 'fast_double_parser', 'fast_float', 'fast_io',
     'fernandovelcic-hexdump', 'ffmpeg', 'fire-hpp', 'fastpfor', 'fixed-containers', 'flac', 'fixed_math', 'flatbush',
     'flatbuffers', 'flatc', 'flatcc', 'flecs', 'flex', 'flann', 'flint', 'flux', 'fltk', 'fmi2', 'fmi3', 'fmtlog',
     'foonathan-lexy', 'folly', 'foonathan-memory', 'foxglove-schemas-protobuf', 'foxi', 'fp16', 'fpgen', 'freealut',
     'foxglove-websocket', 'fpzip', 'forestdb', 'freeimage', 'frozen', 'fribidi', 'freeglut', 'frugally-deep', 'fruit',
     'ftxui', 'function2', 'functionalplus', 'fusepp', 'functions-framework-cpp', 'fxdiv', 'fswatch', 'g3log',
     'gaia-ecs', 'gainput', 'gamenetworkingsockets', 'games101-cgl', 'gamma', 'gcem', 'gdk-pixbuf',
     'gegles-spdlog_setup', 'gdcm', 'genie', 'gemmlowp', 'geos', 'getopt-for-visual-studio', 'geographiclib', 'gettext',
     'gf-complete', 'ginkgo', 'gflags', 'ghc-filesystem', 'gklib', 'glad', 'glbinding', 'glaze', 'glew', 'glext',
     'glfw', 'glib', 'glslang', 'gm2calc', 'glog', 'godot-cpp', 'godot_headers', 'graaf', 'gperftools',
     'google-cloud-cpp', 'googleapis', 'graphene', 'graphthewy', 'greg7mdp-gtl', 'greatest', 'grpc', 'grpc-proto',
     'gsoap', 'gsl-lite', 'gstreamer', 'gtest', 'gtsam', 'gtlab-logging', 'guetzli', 'gurkenlaeufer', 'gumbo-parser',
     'gzip-hpp', 'h5pp', 'hana', 'happly', 'hash-library', 'harfbuzz', 'hayai', 'hazelcast-cpp-client', 'hdf5',
     'hedley', 'hdrhistogram-c', 'heatshrink', 'hffix', 'hfsm2', 'hictk', 'hidapi', 'highfive', 'highs', 'hexl',
     'hippomocks', 'hipony-enumerate', 'highway', 'hiredis', 'homog2d', 'hlslpp', 'http_parser', 'huffman', 'hunspell',
     'hwdata', 'hyperscan', 'hwloc', 'icecream-cpp', 'iceoryx', 'iconfontcppheaders', 'id3v2lib', 'idna',
     'ignition-cmake', 'ignition-math', 'ignition-utils', 'iguana', 'im95able-rea', 'iir1', 'imagemagick', 'imagl',
     'imath', 'imgui', 'ignition-tools', 'imguizmo', 'immer', 'imutils-cpp', 'implot', 'indicators', 'incbin',
     'indirect_value', 'influxdb-cpp', 'imgui-sfml', 'influxdb-cxx', 'inih', 'inipp', 'inja', 'innoextract',
     'intel-ipsec-mb', 'intel-neon2sse', 'intx', 'ios-cmake', 'inversify-cpp', 'iowow', 'ipaddress', 'iphreeqc',
     'isa-l', 'iso8601lib', 'itlib', 'jansson', 'ittapi', 'ixwebsocket', 'jasper', 'jbig', 'jeaiii-itoa', 'jemalloc',
     'jerryscript', 'jfalcou-eve', 'jnk0le_ringbuffer', 'jinja2cpp', 'jpcre2', 'jpeg-compressor', 'jsmn', 'jsbsim',
     'json-c', 'jsoncons', 'json-schema-validator', 'jsoncpp', 'jsonformoderncpp', 'jsonifier', 'json_dto', 'jsonnet',
     'json_struct', 'jtckdint', 'jthread-lite', 'jungle', 'jwasm', 'jwt-cpp', 'kainjow-mustache', 'jxrlib',
     'kaitai_struct_cpp_stl_runtime', 'kangaru', 'kcov', 'kdbindings', 'kealib', 'keychain', 'keystone', 'kickcat',
     'khrplatform', 'kissfft', 'kitten', 'kplot', 'krb5', 'kuba-zip', 'lager', 'laslib', 'lazycsv', 'laszip', 'lcms',
     'ldns', 'lefticus-tools', 'leopard', 'lest', 'leptonica', 'lerc', 'level-zero', 'lexbor', 'libaesgm', 'leveldb',
     'libalsa', 'libarchive', 'libatomic_ops', 'libavif', 'libavrocpp', 'libb2', 'libbigwig', 'libbasisu', 'libbpf',
     'libbacktrace', 'libccd', 'libcds', 'libcbor', 'libcheck', 'libcoap', 'libconfig', 'libconfuse', 'libcoro',
     'libcorrect', 'libcpuid', 'libcuckoo', 'libcvd', 'libcurl', 'libdaemon', 'libde265', 'libdatachannel',
     'libdeflate', 'libdicom', 'libdivide', 'libdmtx', 'libdrawille', 'libdwarf', 'libdxfrw', 'libe57format',
     'libelfin', 'libdispatch', 'libenvpp', 'libepoxy', 'libest', 'libevent', 'libexif', 'libfabric', 'libffi',
     'libfreenect', 'libftp', 'libfork', 'libfuse', 'libfreenect2', 'libgcrypt', 'libgd', 'libgeotiff', 'libgit2',
     'libgphoto2', 'libhal', 'libhydrogen', 'libharu', 'libid3tag', 'libiec61850', 'libheif', 'libigl',
     'libinterpolate', 'libkml', 'libipt', 'libjpeg-turbo', 'libjuice', 'libjxl', 'libltc', 'liblsl', 'libmagic',
     'libmaxminddb', 'libmbus', 'libmikmod', 'libmediainfo', 'libmetalink', 'libmodplug', 'libmorton', 'libmodbus',
     'libmeshb', 'libmpdclient', 'libnet', 'libnfs', 'libnl', 'libnghttp2', 'libnpy', 'libnoise', 'libnuma', 'libnop',
     'libnabo', 'libpcap', 'libphonenumber', 'libplist', 'libpng', 'libpqxx', 'libpopcnt', 'libproperties', 'libpsl',
     'libprotobuf-mutator', 'libq', 'libpointmatcher', 'libqasm', 'libqrencode', 'libraw', 'libsafec', 'libsamplerate',
     'libschrift', 'libsass', 'librdkafka', 'libserial', 'libsersi', 'libressl', 'libsgp4', 'libsixel', 'libslz',
     'libsndfile', 'libsodium', 'libsolace', 'libspatialindex', 'libspng', 'libssh2', 'libsrtp', 'libsvm', 'libsystemd',
     'libtiff', 'libtins', 'libtool', 'libtommath', 'libucl', 'libtorrent', 'libui', 'libunwind', 'libunifex',
     'liburing', 'libusb', 'libusb-compat', 'libuvc', 'libuv', 'libvault', 'libva', 'libvips', 'libverto', 'libversion',
     'libvpx', 'libwebm', 'libwebp', 'libwebsockets', 'libx265', 'libxcrypt', 'libxls', 'libxml2', 'libxlsxwriter',
     'libxmlpp', 'libxslt', 'libyaml', 'libyang', 'libzen', 'libzippp', 'libzip', 'lief', 'lielab', 'lightpcapng',
     'limereport', 'liquid-dsp', 'linmath.h', 'litehtml', 'lightgbm', 'lksctp-tools', 'llama-cpp', 'llnl-units',
     'llhttp', 'lmdb', 'llvm-openmp', 'llvm-core', 'lodepng', 'log.c', 'log4cplus', 'logfault', 'log4cxx', 'logr',
     'loguru', 'luajit', 'ls-qpack', 'luau', 'lunasvg', 'lurlparser', 'lyra', 'lzfse', 'lzham', 'maddy',
     'macdylibbundler', 'magic_enum', 'magnum', 'magnum-extras', 'magnum-integration', 'magnum-plugins', 'mailio',
     'makefile-project-workspace-creator', 'manif', 'manifold', 'mapbox-geometry', 'mapbox-variant', 'mapbox-wagyu',
     'mariadb-connector-cpp', 'marisa', 'matchit', 'mathter', 'materialx', 'mathfu', 'mattiasgustavsson-libs', 'matio',
     'mbedtls', 'mbits-args', 'mbits-diags', 'mbits-lngs', 'mbits-mstch', 'mbits-semver', 'mbits-utfconv', 'mcap',
     'md4qt', 'md4c', 'mdns', 'mdnsresponder', 'mdspan', 'melon', 'meshoptimizer', 'meson', 'metall', 'metis', 'mfast',
     'mgclient', 'microprofile', 'microservice-essentials', 'microtar', 'mikelankamp-fpm', 'mikktspace', 'mini',
     'minhook', 'miniaudio', 'minicoro', 'minimp3', 'minisat', 'mimalloc', 'miniscript', 'minio-cpp', 'minitrace',
     'miniupnpc', 'miniz', 'minizip', 'minizip-ng', 'minmea', 'mlpack', 'mm_file', 'modern-cpp-kafka', 'mold',
     'moltenvk', 'mongo-cxx-driver', 'mongo-c-driver', 'mpark-variant', 'mpir', 'mpg123', 'mozjpeg', 'mpmcqueue',
     'morton-nd', 'mppp', 'msdf-atlas-gen', 'msdfgen', 'msgpack', 'msgpack-c', 'ms-gsl', 'msgpack23', 'msgpack-cxx',
     'msys2', 'mtfmt', 'muparser', 'mujs', 'msix', 'muparserx', 'mysql-connector-cpp', 'naive-tsearch', 'namedtype',
     'nameof', 'nanobench', 'nanodbc', 'nanoflann', 'nanorange', 'nanomsg', 'nanort', 'nativefiledialog', 'nanosvg',
     'ncurses', 'neargye-semver', 'net-snmp', 'netcdf', 'nfrechette-acl', 'nextsilicon-cpp-subprocess', 'nifti_clib',
     'nghttp3', 'ninja', 'nlohmann_json', 'nlopt', 'nmos-cpp', 'nodeeditor', 'norm', 'nodesoup', 'nodejs', 'ntv2',
     'nsync', 'nmslib', 'nudb', 'numcpp', 'nv-codec-headers', 'nuklear', 'nuraft', 'nvtx', 'oatpp-libressl', 'oatpp',
     'oatpp-postgresql', 'oatpp-openssl', 'oatpp-sqlite', 'oatpp-swagger', 'oatpp-websocket', 'observer-ptr-lite',
     'oboe', 'ocilib', 'octo-encryption-cpp', 'octo-keygen-cpp', 'octo-logger-cpp', 'octo-wildcardmatching-cpp',
     'octomap', 'ogdf', 'ohnet', 'oniguruma', 'onnx', 'open-dis-cpp', 'open-simulation-interface', 'onnxruntime',
     'open62541pp', 'onetbb', 'onedpl', 'openal-soft', 'open62541', 'openassetio', 'openblas', 'opencl-clhpp-headers',
     'opencascade', 'opencl-headers', 'opencl-icd-loader', 'openddl-parser', 'opencolorio', 'opene57', 'openfx',
     'openfbx', 'opengl-registry', 'opengv', 'opendis6', 'openh264', 'openjpeg', 'openjph', 'openldap', 'openmvg',
     'openscenegraph', 'openslide', 'openssh', 'opensubdiv', 'openimageio', 'opentelemetry-cpp', 'opentracing-cpp',
     'opentelemetry-proto', 'opentrackio-cpp', 'openvdb', 'openxlsx', 'openvr', 'openvino', 'optional-lite', 'opus',
     'opusfile', 'osgearth', 'orcania', 'osmanip', 'ouster_sdk', 'osqp', 'outcome', 'ozz-animation', 'out_ptr',
     'p-ranav-glob', 'packio', 'pagmo2', 'pango', 'parallel-hashmap', 'parg', 'p7zip', 'parson', 'parlayhash',
     'patchelf', 'pathie-cpp', 'paho-mqtt-c', 'paho-mqtt-cpp', 'pbtools', 'pcapplusplus', 'pcg-cpp', 'pciutils', 'pcre',
     'pcre2', 'pdal', 'pdcurses', 'pdf-writer', 'pdfgen', 'perf', 'pdqsort', 'perlinnoise', 'perfetto', 'pgm-index',
     'physfs', 'picojson', 'picobench', 'picosha2', 'pipes', 'pkgconf', 'platform.converters', 'platform.delegates',
     'platform.equality', 'platformfolders', 'pistache', 'platform.hashing', 'platform.exceptions', 'playrho',
     'plf_colony', 'plf_indiesort', 'plf_list', 'plf_nanotimer', 'plf_queue', 'plutosvg', 'plog', 'plusaes', 'plutovg',
     'pocketfft', 'poco', 'podofo', 'poly2tri', 'polylabel', 'popl', 'plf_stack', 'polymorphic_value',
     'polylineencoder', 'portable-file-dialogs', 'poshlib', 'poselib', 'pranav-csv2', 'pprint', 'pretty-name',
     'procxx-boost-ext-simd', 'pro-mdnsd', 'proj', 'primesieve', 'prometheus-cpp', 'proposal', 'protobuf', 'protopuf',
     'protobuf-c', 'protozero', 'psyinf-gmtl', 'ptex', 'psimd', 'pthreadpool', 'pugixml', 'proxy', 'pulseaudio',
     'pupnp', 'pybind11', 'pybind11_json', 'qarchive', 'qcbor', 'pystring', 'qcoro', 'qhull', 'qoixx', 'qpdf',
     'qr-code-generator', 'qpoases', 'qt-advanced-docking-system', 'qtawesome', 'quantlib', 'quaternions', 'quazip',
     'quickcpplib', 'quickfast', 'quickfix', 'quickjs', 'quirc', 'quill', 'qxlsx', 'qxmpp', 'r8brain-free-src',
     'rabbitmq-c', 'rang', 'range-v3', 'rangesnext', 'rangeless', 'rapidcheck', 'rapidcsv', 'rapidhash', 'rapidjson',
     'raylib', 'rapidyaml', 'rc_ptr', 'rapidfuzz', 'rdma-core', 're2c', 'reactiveplusplus', 'read-excel',
     'readerwriterqueue', 'rebound', 'recastnavigation', 'reckless', 'redboltz-mqtt_cpp', 'rectpack2d',
     'redis-plus-plus', 'redradist-icc', 'refl-cpp', 'reflect-cpp', 'replxx', 'reproc', 'resiprocate', 'resource_pool',
     'restbed', 'rgbcx', 'rg-etc1', 'restinio', 'ring-span-lite', 'roaring', 'robin-hood-hashing', 'rocket', 'rocksdb',
     'rotor', 'rpclib', 'rtklib', 'rsync', 'rtmidi', 'rttr', 'runtimeqml', 'rusty-cpp', 'ruby', 'rvo2', 's2let',
     's2geometry', 'safeint', 'rxcpp', 'sail', 'sassc', 'samurai', 'sbepp', 'samarium', 'scippp', 'scip', 'scnlib',
     'scope-lite', 'screen_capture_lite', 'sdbus-cpp', 'sdl_image', 'sdl_net', 'sdl_ttf', 'seadex-essentials',
     'seasocks', 'seadex-genesis', 'semimap', 'semver.c', 'sentry-breakpad', 'serdepp', 'seqan3', 'serial',
     'sentry-crashpad', 'sentry-native', 'sfml', 'shapelib', 'shaderc', 'signals-light', 'shield', 'sigslot', 'simd',
     'simde', 'simdutf', 'simdjson', 'simfil', 'simple-yaml', 'simple_enum', 'sjson-cpp', 'sleef', 'sioclient',
     'skyr-url', 'snitch', 'snappy', 'snowhouse', 'so5extra', 'sobjectizer', 'sol2', 'sokol', 'soci', 'sole',
     'sonic-cpp', 'sophus', 'soplex', 'source_location', 'span-lite', 'spectra', 'sparrow', 'spdlog', 'speedb',
     'spirv-cross', 'spirv-headers', 'spirv-tools', 'spix', 'spscqueue', 'splunk-opentelemetry-cpp', 'sqlcipher',
     'sqlite3mc', 'sqlitecpp', 'sqlitemap', 'sqlite_orm', 'sqlpp11-connector-sqlite3', 'sqlpp11', 'squirrel', 'ssht',
     'statistic', 'status-code', 'statslib', 'status-value-lite', 'stdgpu', 'stduuid', 'stlab', 'streaming-percentiles',
     'stella-cv-fbow', 'string-view-lite', 'stringtoolbox', 'stringzilla', 'structopt', 'strong_type', 'st_tree',
     'streamvbyte', 'suyash-ulid', 'sundials', 'svector', 'svgpp', 'svtjpegxs', 'symengine', 'swig', 'systemc',
     'tabulate', 'taglib', 'taocpp-sequences', 'taocpp-json', 'taocpp-operators', 'taocpp-taopq', 'taocpp-tuple',
     'taywee-args', 'taskflow', 'tcb-span', 'tclap', 'termcolor', 'tensorpipe', 'tensorflow-lite', 'tcsbank-uconfig',
     'tcsbank-uri-template', 'teemo', 'tesseract', 'tgbot', 'thelink2012-any', 'thorvg', 'threadpool', 'thrift',
     'tidwall-neco', 'tidy-html5', 'timsort', 'tiledb', 'tiny-aes-c', 'tiny-bignum-c', 'tiny-dnn', 'tiny-regex-c',
     'thrust', 'tiny-utf8', 'tinyad', 'tinyalsa', 'tinycbor', 'tinycolormap', 'tinycthread', 'tinycthreadpool',
     'tinydir', 'tinyexif', 'tinyexr', 'tinygltf', 'tinymidi', 'tinyobjloader', 'tinyply', 'tinyspline', 'tinyxml2',
     'tixi3', 'tl-expected', 'tl-function-ref', 'tl-optional', 'tl-ranges', 'tmxlite', 'toml11', 'tomlplusplus', 'toon',
     'transwarp', 'tracy', 'tree-gen', 'trantor', 'tree-sitter', 'tree-sitter-c', 'tree-sitter-cpp', 'tree-sitter-sql',
     'trompeloeil', 'tree-sitter-cql', 'tsl-hat-trie', 'tscns', 'tsl-array-hash', 'tsl-robin-map', 'tsl-hopscotch-map',
     'tsl-ordered-map', 'troldal-zippy', 'tsl-sparse-map', 'tuplet', 'turtle', 'tweeny', 'tweenerspp', 'type_safe',
     'twitchtv-libsoundtrackutil', 'twitch-native-ipc', 'ua-nodeset', 'ulfius', 'uncrustify', 'unicorn', 'uni-algo',
     'units', 'unity', 'unleash-client-cpp', 'unordered_dense', 'univalue', 'unqlite', 'urdfdom', 'userspace-rcu',
     'uriparser', 'urdfdom_headers', 'usrsctp', 'utf8.h', 'usockets', 'utfcpp', 'uthash', 'utf8proc', 'v-hacd',
     'variant-lite', 'valijson', 'vcglib', 'vectorclass', 'uwebsockets', 'vectorial', 'veque', 'very-simple-smtps',
     'vectorscan', 'verilator', 'vigra', 'velodyne_decoder', 'vincentlaucsb-csv-parser', 'vir-simd', 'visit_struct',
     'vk-bootstrap', 'volk', 'vorbis', 'vulkan-loader', 'vtu11', 'vulkan-headers', 'vulkan-memory-allocator',
     'vulkan-validationlayers', 'vvenc', 'wasm-micro-runtime', 'wasmtime-cpp', 'websocketpp', 'wavelet_buffer',
     'wg21-linear_algebra', 'watcher', 'wglext', 'whereami', 'whisper-cpp', 'wide-integer', 'wildcards', 'wildmidi',
     'winreg', 'winflexbison', 'wiringpi', 'wise_enum', 'winmd', 'wolfssl', 'wslay', 'wyhash', 'wxwidgets', 'xbyak',
     'xege', 'xerces-c', 'xlnt', 'xlsxio', 'xmlsec', 'xpack', 'xorstr', 'xnnpack', 'xoshiro-cpp', 'xproperty', 'xsimd',
     'xtensor', 'xxhash', 'yajl', 'yaml-cpp', 'yaclib', 'xxsds-sdsl-lite', 'yandex-ozo', 'yasm', 'yder', 'ydcpp-tcpcat',
     'yoga', 'yomm2', 'yyjson', 'zbar', 'zeromq', 'zeus_expected', 'zimg', 'yojimbo', 'zint', 'zlib', 'zlib-ng',
     'zmarok-semver', 'zmqpp', 'zpp_bits', 'zstr', 'zpp_throwing', 'zopfli', 'zstd', 'zxing-cpp', 'zziplib', 'zyre',
     'iproute2', 'app-pym', 'mini-xml', 'open-uri-cached', 'lsposed', 'libsdl', 'goahead_webserver', 'nmealib',
     'can_utils', 'createrepo_c', 'postgresql', 'wxsqlite', 'o2dlm', 'jvarkit', 'UltraVNC', 'libmdb', 'libav',
     'gnome-screensaver', 'lame', 'Ne10', 'bullet', 'libcxx', 'sigar', 'open_vm_tools', 'xpdf', 'coreclr', 'mingw',
     'android-gif-drawable', 'STLport', 'openpbs', 'fcgi', 'pytorch', 'apollo-platform', 'mmkv', 'openssl', 'sqlite',
     'suiteparse', 'networkmanager', 'pjsip', 'atomicparsley', 'mapbox-gl-native', 'nghttp2', 'alsa-plugins', 'nanopb',
     'libzbar', 'rng-tools', 'mmngr', 'fresco', 'mars', 'netbsd', 'boringssl', 'luasocket', 'juce', 'curl',
     'libfacedetection', 'ntfs-3g', 'iputils', 'one_true_awk', 'exfat', 'tensorflow', 'opentype_sanitiser', 'xdelta3',
     'minijail', 'libflac', 'incubator-mxnet', 'sonic', 'ncnn', 'godot', 'iniparser', 'marisa-trie', 'paho-mqtt',
     'gfxreconstruct', 'libvixl', 'aubio', 'azure-iot-sdk-c', 'kaldi', 'mindspore', 'bolt-noah', 'conscrypt',
     'procrank', 'tcpdump', 'chromaprint', 'libexpat', 'Amazon FreeRTOS', 'libicu', 'opencv', 'dmlc', 'alvr',
     'traffic_server', 'skia', 'mupdf', 'jbig2dec', 'fontforge', 'javascriptcore', 'fdk-aac', 'fuse',
     'android-hardware-qcom-audio-caf', 'threading_building_blocks', 'piex', 'giflib', 'abcm2ps', 'selinux',
     'linux_kernel', 'speex', 'wireshark', 'mksh', 'libopusenc', 'python', 'speexdsp', 'alsa-utils', 'linux-audit',
     'vixie-cron', 'glibc', 'vsomeip', 'alsa-lib', 'mongoose', 'apache_harmony', 'Amazon Corretto 8', 'sysvinit',
     'wireless-tools', 'dhcpcd', 'wpa_supplicant', 'miniupnp', 'Util-linux', 'tinyproxy', 'sigma-dut', 'pimd', 'shadow',
     'perl', 'popt', 'libavformat', 'htop', 'nss-mdns', 'lrzsz', 'bluez', 'libass', 'sysfsutils', 'linux-pam', 'strace',
     'iperf3', 'dlt-daemon', 'CyaSSL', 'arm-trusted-firmware', 'mosquitto', 'xmp-toolkit-sdk', 'gpsd', 'ipsec-tools',
     'android-nn-driver', 'assimp', 'suricata', 'armnn', 'mono', 'libhtp', 'liblinear', 'cups', 'toybox', 'libgdx',
     'halide', 'qt_mobility', 'android-packages-apps-Phone', 'crf++', 'dosfstools', 'openexr', 'reshade', 'jffi',
     'libtomcrypt', 'asciidoctor', 'coderay', 'jansi', 'netty', 'libopenmpt', 'systemd', 'ncat', 'zlog',
     'CommonAPI C++ Core Runtime', 'Common API C++ dbus runtime', 'lighttpd', 'openavnu', 'ladvd', 'libexecs', 'yafc',
     'pacparser', 'flatpak', 'libansilove', 'dcraw', 'rarpd', 'memtool', 'xbanish', 'apngasm', 'libfsntfs', 'radare',
     'comskip', 'dbus-broker', 'libgusb', 'cassiopee', 'connect-proxy', 'unixodbc', 'sratom', 'litl', 'libjsonparser',
     'newt', 'roguenarok', 'less', 'mate-utils', 'open-isns', 'growlight', 'x11-touchscreen-calibrator', 'ngrep',
     'wl-clipboard', 'pqiv', 'kodi-pvr-teleboy', 'netdiscover', 'kannel', 'retroarch', 'heimdal', 'gmime', 'flite',
     'grok', 'mseed2sac', 'globus-gss-assist', 'radsecproxy', 'haproxy', 'gntp-send', 'netatalk', 'rauc',
     'remote-logon-service', 'profanity', 'elektroid', 'espeakup', 'libproxy', 'gconjugue', 'mednaffe', 'mplayer',
     'encfs', 'evince', 'flint-arb', 'purelibc', 'light-locker', 'r-cran-randomfields', 'yubico-piv-tool', 'genext2fs',
     'lxcfs', 'libevhtp', 'fsarchiver', 'libnfc', 'kodi-visualization-pictureit', 'faad2', 'dropbear', 'mp4v2',
     'live555', 'nginx', 'x265', 'exfatprogs', 'libiio', 'collectd', 'corefoundation', 'weex', 'u-boot', 'chat',
     'googletest', 'ceph', 'AliceVision', 'sudo', 'pwgen', 'linuxptp', 'simplejson', 'sysstat', 'rsyslog',
     'libfastjson', 'libndp', 'vsftpd', 'grid_map', 'xl2tpd', 'optee_client', 'libdnet', 'libcap-ng', 'wazuh', 'libcli',
     'lsof', 'vspmif_drv', 'mmngr_lib', 'kudu', 'inotify-tools', 'Bento4 portable MP4 file format library', 'picotts',
     'usb-modeswitch', 'mediainfolib', 'aircrack-ng', 'facebook-folly', 'openvswitch', 'gpac', 'powerdns', 'freerdp',
     'meinheld', 'rtpproxy', 'charybdis', 'passenger', 'libetpan', 'netdata', 'chrome', 'librsvg', 'freelan', 'goahead',
     'procmail', 'peg-markdown', 'exim', 'clang', 'graphics_magick', 'kismet', 'uclibc', 'nagios', 'ircd-hybrid',
     'freecad', 'tmux', 'pidgin', 'syslog-ng', 'gnome-keyring', 'rspamd', 'dpkg', 'rdesktop', 'opensolaris',
     'freeradius', 'l2tpns', 'maradns', 'pacemaker', 'glusterfs', 'cgminer', 'gvfs', 'espruino', 'jabberd2',
     'transmission', 'tntnet', 'mutt', 'firefox', 'tcsh', 'openvpn', 'fvwm', 'openwrt', 'clamav', 'appweb', 'quassel',
     'libupnp', 'neomutt', 'librsync', 'xastir', 'ompl', 'newsbeuter', 'openwsman', 'cronie', 'knot-resolver', 'xchat',
     'rrdtool', 'opencc', 'elinks', 'flightgear', 'gobby', 'icinga', 'corosync', 'gnucash', 'brltty', 'chmlib', 'cmus',
     'postgis', 'graphviz', 'mysql_workbench', 'domoticz', 'subversion', 'dovecot', 'libusbmuxd', 'ndpi', 'citadel',
     'asterisk', 'atheme', 'bwm-ng', 'xrdp', 'ytnef', 'xscreensaver', 'dpdk', 'qbittorrent', 'gimp', 'swfmill',
     'inspircd', 'libgadu', 'winsparkle', 'bitlbee', 'fastjar', 'mesos', 'mongodb', 'monero', 'opensips', 'illumos',
     'yubico-pam', 'telegram-desktop', 'unrealircd', 'darwin', 'util-vserver', 'kde-workspace', 'pure-ftpd',
     'pam-mysql', 'libgtop', 'abrt', 'librelp', 'alpine', 'teeworlds', 'sthttpd', 'libxsmm', 'gnupg', 'recommender',
     'libcaca', 'gdnsd', 'mruby', 'chrony', 'openconnect', 'beanstalkd', 'gifsicle', 'djbdns', 'privoxy', 'dash',
     'mcabber', 'mdbtools', 'strongswan', 'percona-xtradb-cluster', 'pngcrush', 'procps', 'irssi', 'hybris', 'yadifa',
     'libraptor', 'packagekit', 'putty', 'xinetd', 'gparted', 'mariadb', 'aria2', 'gdal', 'vips', 'audacity', 'librest',
     'graphite2', 'gfs2-utils', 'fetchmail', 'mod_wsgi', 'openttd', 'ardour', 'rhythmbox', 'openafs', 'monit', 'lftp',
     'ibus', 'htdig', 'autotrace', 'atari800', 'bareos', 'pcsc-lite', 'thunderbird', 'openipmi', 'cygwin', 'libical',
     'freebsd', 'libgdata', 'libsolv', 'libofx', 'swftools', 'liblas', 'catdoc', 'weechat', 'colord', 'quagga',
     'bitcoin', 'amarok', 'modsecurity', 'polarssl', 'openbsd', 'postgres', 'mumble', 'libguestfs', 'osquery', 'kile',
     'libreoffice', 'libimobiledevice', 'libmtp', 'xine', 'redis', 'snort', 'icu4c', 'partclone', 'firebird',
     'multipath-tools', 'gupnp', 'memcached', 'swi-prolog', 'qemu', 'newlib', 'winscp', 'imapfilter', 'pdfedit',
     'slic3r', 'varnish', 'trojita', 'rawstudio', 'firejail', 'picocom', 'wkhtmltopdf', 'uclibc-ng', 'tigervnc',
     'libmwaw', 'lldpd', 'ioquake3', 'chocolate-doom', 'epiphany', 'ktorrent', 'gcab', 'liblouis', 'libvorbis',
     'mapserver', 'lcdproc', 'alsaplayer', 'gtk-vnc', 'kerberos', 'ntpsec', 'ansible', 'ambari', 'xorg-server',
     'http_server', 'boinc', 'gitlab', 'mysql', 'cups-filters', 'rxvt-unicode', 'stunnel', 'portable_runtime', 'zabbix',
     'battle_for_wesnoth', 'ht_editor', 'nmap', 'libfishsound', 'proftpd', 'motion', 'android', 'ruby_on_rails',
     'file_roller', 'squid', 'bftpd', 'thermald', 'tcmu-runner', 'check_mk', 'ctools', 'yaws', 'keepalived', 'openswan',
     'namazu', 'sblim-sfcb', 'lightdm', 'mecab', 'condor', 'polipo', 'viewvc', 'vm_virtualbox', 'amule', 'openoffice',
     'sympa', 'debian_linux', 'gnome-shell', 'uw-imap', 'pillow', 'ocaml', 'revelation', 'monkey_http_daemon', 'opensc',
     'freeipa', 'tightvnc', 'kay_framework', 'mailman', 'libmspack', 'tex_live', 'cobbler', 'udisks', 'sogo', 'webmail',
     'mosh', 'dibbler', 'unbound', 'the_sleuth_kit', 'logrotate', 'web_toolkit', 'silverlight', 'shim', 'docker',
     'foomatic-filters', 'tetex', 'sssd', 'unzip', 'cyrus_imap_server', 'xterm', 'horizon', 'smb4k', 'ubuntu', 'itop',
     'libmp3splt', 'bfgminer', 'electron', '.net_framework', 'imap', 'sumatrapdf', 'tcptrack', 'oprofile', 'libsoup',
     'couchdb', 'augeas', 'imlib2', 'odoo', 'trac', 'portage', 'recursor', 'sfntly', 'opencryptoki', 'miniupnpd',
     'forms', 'csound', 'snack_sound_toolkit', 'mod_perl', 'publisher', 'mlterm', 'tidy', 'xtrabackup', 'libcgroup',
     'balsa', 'spamassassin', 'entity_api', 'bchunk', 'ettercap', 'opensuse_osc', 'bitcoin-qt', 'koffice',
     'netwide_assembler', 'kamailio', 'gnome_online_accounts', 'ecryptfs-utils', 'openslp', 'picotcp', 'konqueror',
     'kubernetes', 'unrar', 'oftc-hybrid', 'kpdf', 'cfingerd', 'tk_toolkit', 'mathopd', 'tripwire', 'argyllcms',
     'pound', 'neutron', 'pgpdump', 'chakracore', 'lrzip', 'webkit', 'x_server', 'libgdiplus', 'bitcoind', 'rssh',
     'libgsf', 't1lib', 'bsdgames', 'afflib', 'yara', 'ntopng', 'libreswan', 'isync', 'darwin_streaming_server',
     'mod_fcgid', 'mini_httpd', 'simpleproxy', 'remote_plug_in_executor', 'browser', 'appstream', 'yassl', 'net6',
     'zammad', 'prosody', 'grub2', 'evolution', 'slurm', 'c-icap', 'frox', 'qcms', 'authoritative', 's3ql', 'radare2',
     'neon', 'scintilla', 'unrtf', 'silc_toolkit', 'roaraudio', 'pam-pgsql', 'openwebif', 'zrtpcpp', 'opensmtpd',
     'libspf2', 'filezilla', 'sgminer', 'cracklib', 'lm_sensors', 'shibboleth-sp', 'freeciv', 'axtls', 'gegl', 'beaker',
     'kleopatra', 'libcsp', 'libao', 'sam2p', 'libthai', 'solaris', 'ossec', 'mod_auth_openidc', 'mcrypt', 'yabb',
     'libwmf', 'vtun', 'foomatic', 'freeware_advanced_audio_decoder_2', 'mldonkey', 'sniffit', 'freeswitch',
     'kscreenlocker', 'streamripper', 'pygresql', 'libshout', 'optipng', 'gnumeric', 'blueman', 'bento4', 'mercurial',
     'antiword', 'adplug', 'wavpack', 'kmail', 'ssmtp', 'kdegraphics', 'webkitgtk', 'ncompress', 'zpanel', 'blink',
     'libvncserver', 'greenbone_security_assistant', 'htmldoc', 'frrouting', 'guilt', 'kword', 'pysaml2', 'libvirt',
     'spacewalk', 'lhasa', 'messagelib', 'fusionforge', 'bochs', 'directfb', 'kura', 'libotr', 'wine', 'amanda',
     'ncpfs', 'denyhosts', 'mod_auth_mellon', 'proxygen', 'icecast', 'electrum', 'proxytunnel', 'libmatroska',
     'metasploit', 'wordnet', 'tcpreplay', 'calibre', 'readstat', 'evolution-data-server', 'potrace',
     'yerase%27s_tnef_stream_reader', 'shellinabox', 'glance', 'mountall', 'webrtc', 'libzypp', 'runc', 'hexchat',
     'hmailserver', 'home-assistant', 'canto_curses', 'redcarpet', 'libgxps', 'asp.net_core', 'jhead', 'exmpp', 'obby',
     'vorbis-tools', 'ppc64-diag', 'konversation', 'contiki', 'lsyncd', 'plasma-workspace', 'p3scan', 'libming',
     'isoqlog', 'slock', 'kde4libs', 'aide', 'op-tee', 'libesmtp', 'projectpier', 'eterm', 'riot', 'vala', 'deluge',
     'sound_exchange', 'sddm', 'crafty', 'lynx', 'vzctl', 'ftpd', 'gnome-subtitles', 'pigz', 'bionic', 'nullmailer',
     'lepton', 'htslib', 'dropbear_ssh', 'tnef', 'fireflymediaserver', 'cxxtools', 'qpid', 'open_build_service',
     'pngquant', 'rinetd', 'powerpc-utils', 'latex2rtf', 'hivex', 'mysql-ocaml', 'imageworsener', 'tinydtls',
     'squashfs', 'abiword', 'yelp', 'yast2', 'mimetex', 'pyfribidi', 'gtetrinet', 'pgbouncer', 'desktop', 'snorby',
     'hhvm', 'libebml', 'afuse', 'libbpg', 'c.p.sub', 'brave', 'winpcap', 'jpegsnoop', 'cgmanager', 'das_watchdog',
     'swift3', 'stb_vorbis', 'libevt', 'geary', 'tcptraceroute', 'proxychains-ng', 'gnuplot', 'bubblewrap',
     'afnetworking', 'boolector', 'atop', 'autojump', 'chafa', 'coturn', 'freetds', 'gerbv', 'glewlwyd', 'grilo',
     'gssproxy', 'ipmitool', 'fastd', 'jpegoptim', 'libseccomp', 'libpff', 'nbdkit', 'openfortivpn', 'openrc',
     'pdfresurrect', 'postsrsd', 'usbview', 'vcftools', 'x11vnc', 'edk2', 'libu2f-host', 'bsdiff', 'steghide', 'envoy',
     'mongoose-os', 'toaruos', 'zephyr', 'rtl_433', 'zerotierone', 'iipsrv', 'cinder', 'snapd', 'faust', 'bcos',
     'astc-encoder', 'didiwiki', 'otfcc', 'scylla', 'tpm2-tools', 'loramac-node', 'iotjs', 'gps-sdr-sim', 'accel-ppp',
     'timescaledb', 'blynk-library', 'guacamole-server', 'libmobi', 'anakin', 'incubator-doris', 'lsquic-client',
     'tpm2-tss', 'tinytoml', 'tifig', 'tmate-ssh-server', 'lighttpd1.4', 'mbed-os', 'janet', 'moddable', 'platinum',
     'xhyve', 'aurora', 'ada-idna', 'air-ctl', 'libmysofa', 'adios2', 'aklomp-base64', 'aixlog', 'aliyun-oss-c-sdk',
     'aliyun-oss-cpp-sdk', 'anax', 'ampl-asl', 'alpaka', 'ampl-mp', 'amd-amf', 'angle', 'ankurvdev-embedresource',
     'args', 'apsi', 'argumentum', 'arcticdb-sparrow', 'arpack-ng', 'aricpp', 'arrayfire', 'ashes', 'asiochan', 'asock',
     'asynch', 'astr', 'async-mqtt', 'atliac-minitest', 'audioengine', 'audit', 'aurora-au', 'avro-c', 'avro-cpp',
     'awlib', 'azmq', 'azure-c-shared-utility', 'azure-core-amqp-cpp', 'azure-core-tracing-opentelemetry-cpp',
     'azure-core-cpp', 'azure-identity-cpp', 'azure-data-tables-cpp',
     'azure-messaging-eventhubs-checkpointstore-blob-cpp', 'azure-kinect-sensor-sdk', 'azure-messaging-eventhubs-cpp',
     'azure-security-attestation-cpp', 'azure-security-keyvault-administration-cpp',
     'azure-security-keyvault-certificates-cpp', 'azure-security-keyvault-keys-cpp',
     'azure-security-keyvault-secrets-cpp', 'azure-storage-common-cpp', 'azure-storage-blobs-cpp',
     'azure-storage-files-datalake-cpp', 'azure-storage-files-shares-cpp', 'baresip-libre', 'bark', 'azure-uhttp-c',
     'azure-storage-queues-cpp', 'azure-uamqp-c', 'azure-umqtt-c', 'barkeep', 'basisu', 'bcg729', 'bddisasm', 'bext-di',
     'bext-sml', 'bit7z', 'bext-sml2', 'bext-wintls', 'bext-ut', 'blake3', 'blickfeld-qb2', 'blitz',
     'bloomberg-quantum', 'bluescarni-tanuki', 'boost-cmake', 'braft', 'blosc', 'boost-build', 'brpc', 'buck-yeh-bux',
     'buck-yeh-bux-sqlite', 'bond', 'bustache', 'bw-sqlitemap', 'bw-tempdir', 'bsio', 'c89stringutils', 'bxzstr',
     'camport3', 'cachelib', 'catch-classic', 'catch2', 'cccapstone', 'cddlib', 'ceres', 'chipmunk', 'cinatra',
     'clblast', 'clipboardxx', 'clfft', 'cld3', 'clockutils', 'clrng', 'cialloo-rcon', 'clue', 'cmakerc', 'cmark',
     'coin-or-cbc', 'coin-or-cgl', 'coin', 'coin-or-ipopt', 'collada-dom', 'cmark-gfm', 'conjure-enum', 'color-console',
     'constexpr', 'compoundfilereader', 'convectionkernels', 'constexpr-contracts', 'coolprop', 'coroutine',
     'cpp-base64', 'correlation-vector-cpp', 'cpp-async', 'cpp-pinyin', 'cpp-kana', 'cpp-redis', 'cpp-timsort',
     'cppcms', 'cppad', 'cppcoro', 'cppgraphqlgen', 'cppp-reiconv', 'cserialport', 'cpuid', 'cppmicroservices',
     'cpprealm', 'ctbignum', 'ctemplate', 'ctbench', 'cppwinrt', 'cwapi3d', 'dbow2', 'daxa', 'datraw', 'cubeb', 'dbow3',
     'delaunator-cpp', 'deniskovalchuk-libftp', 'ctstraffic', 'dimcli', 'dingo', 'discreture', 'dlfcn-win32',
     'directx-dxc', 'directxmath', 'directxtk', 'directxmesh', 'directxtk12', 'doctest', 'directxtex', 'discord-rpc',
     'dp-thread-pool', 'drekar-launch-process-cpp', 'duilib', 'dukglue', 'dumb', 'dxcam-cpp', 'dyno', 'earcut-hpp',
     'easycl', 'easyhook', 'eathread', 'dxut', 'ed25519', 'ebml', 'egl-registry', 'entt', 'effects11', 'evpp', 'faiss',
     'fann', 'fameta-counter', 'fastlz', 'ereignis', 'fastor', 'fawdlstty-libfv', 'fbthrift', 'fenster', 'ffnvcodec',
     'fixed-string', 'fineftp', 'fizz', 'flagpp', 'flash-runtime-extensions', 'flashlight-sequence', 'flat',
     'flashlight-text', 'fluidlite', 'fluidsynth', 'fmi4cpp', 'font-chef', 'forge', 'flashlight-cpu', 'flashlight-cuda',
     'freetype-gl', 'ftgl', 'fuzzylite', 'future-config', 'fxaudio', 'gapp', 'gaussianlib', 'genann', 'gasol',
     'geogram', 'ggml', 'gl3w', 'globjects', 'glfw3', 'glui', 'gpgmm', 'gppanel', 'gmmlib', 'grantlee', 'grppi',
     'guilite', 'gloo', 'gul17', 'hdr-histogram', 'h5py-lzf', 'hexi', 'hareflow', 'hikogui', 'hnswlib', 'htscodecs',
     'hypodermic', 'if97', 'im3d', 'imageinfo', 'idyntree', 'imgui-node-editor', 'implot3d', 'infoware',
     'iowa-hills-dsp', 'intrusive-shared-ptr', 'ismrmrd', 'itay-grudev-singleapplication', 'itsy-bitsy',
     'jaeger-client-cpp', 'jhasse-poly2tri', 'jigson', 'joltphysics', 'jinja2cpplight', 'josuttis-jthread',
     'json-rpc-cxx', 'kdalgorithms', 'json5-parser', 'kdsingleapplication', 'kdreports', 'keccak-tiny',
     'kdstatemachineeditor', 'kerbal', 'kf5syntaxhighlighting', 'kissnet', 'knet', 'kleidiai', 'kvasir-mpl',
     'launch-darkly-server', 'lazy-importer', 'lastools', 'kuku', 'krabsetw', 'lfreist-hwinfo', 'libadlmidi', 'lib3mf',
     'libaes-siv', 'libassert', 'libaribcaption', 'libbson', 'libcrafter', 'libcopp', 'libcred', 'libcsv',
     'libdjinterop', 'libebur128', 'liberasurecode', 'libgo', 'libfort', 'libhdfs3', 'libhsplasma', 'libhv',
     'libeventheader-decode', 'libeventheader-tracepoint', 'libilbc', 'libics', 'libguarded', 'libkeyfinder',
     'libleidenalg', 'liblo', 'liblrc', 'liblsquic', 'libmatio-cpp', 'libmariadb', 'libmem', 'libmesh', 'libmicrodns',
     'libmultisense', 'libmidi2', 'libmt32emu', 'libmupdf', 'libobfuscate', 'libnick', 'libmysql', 'libopnmidi',
     'libosdp', 'libpmemobj-cpp', 'libqglviewer', 'libqcow', 'libqtrest', 'librabbitmq', 'libsbml', 'libraqm',
     'libsbsms', 'libsercomm', 'libsmb2', 'libspnav', 'libsonic', 'libsrt', 'libremidi', 'libtess2', 'libtheora',
     'libtcod', 'libudis86', 'libtracepoint', 'libtracepoint-control', 'libudns', 'libunibreak', 'libusbp', 'libvhdi',
     'libtracepoint-decode', 'libvmaf', 'libvmdk', 'libxdiff', 'libxmlmm', 'linalg', 'libzim', 'linmath',
     'lionkor-commandline', 'libwandio', 'llgi', 'llfio', 'licensepp', 'llgl', 'ltla-aarand', 'ltla-cppirlba',
     'ltla-cppkmeans', 'lockpp', 'ltla-powerit', 'lua-compat53', 'luabridge', 'luabridge3', 'luasec', 'ltla-knncolle',
     'ltla-umappp', 'luminoengine', 'lunarg-vulkantools', 'lwlog', 'luafilesystem', 'lzav', 'lzokay', 'magic-get',
     'mapbox-geojson-vt-cpp', 'mapbox-polylabel', 'mapbox-geojson-cpp', 'marchingcubecpp', 'marzbanpp', 'mathc', 'marl',
     'mapnik', 'matplotlib-cpp', 'matroska', 'mchehab-zbar', 'mcpp', 'meekrosoft-fff', 'metrohash', 'memorymodule',
     'mdl-sdk', 'mfx-dispatch', 'mgnlibs', 'michaelmiller-sec21', 'mimicpp', 'minc', 'miniply', 'minifb',
     'minisat-master-keying', 'modp-base64', 'morphologica', 'mpark-patterns', 'mqtt-cpp', 'mman', 'msinttypes', 'msh3',
     'ms-gltf', 'mstch', 'mtlt', 'ms-ifc-sdk', 'msquic', 'munit', 'murmur3', 'murmurhash', 'mysvac-jsonlib', 'mvfst',
     'nano-signal-slot', 'nana', 'nanogui', 'nanojsonc', 'nanoprintf', 'nativefiledialog-extended', 'nanovg',
     'nayuki-qr-code-generator', 'ned14-internal-quickcpplib', 'neon2sse', 'netcdf-c', 'netcdf-cxx4', 'netcpp',
     'ndis-driver-library', 'nethost', 'nifly', 'ngtcp2', 'nlohmann-fifo-map', 'nngpp', 'nnpack', 'node-addon-api',
     'nowide', 'nt-wrapper', 'nu-book-zxing-cpp', 'nrf-ble-driver', 'numactl', 'nvidia-cutlass', 'nvtt', 'nyan-lang',
     'oatpp-consul', 'oatpp-curl', 'oatpp-mongo', 'oatpp-ssdp', 'oatpp-zlib', 'ogre', 'offscale-libetcd-cpp',
     'ogre-next', 'onnx-optimizer', 'onednn', 'opencensus-cpp', 'opencl', 'opencsg', 'opencv2', 'opencv3',
     'onnxruntime-gpu', 'opencv4', 'opendnp3', 'openigtlink', 'openni2', 'openmama', 'optimus-cpp',
     'opentelemetry-cpp-contrib-version', 'openxr-loader', 'orocos-kdl', 'orange-math', 'p-ranav-csv', 'palsigslot',
     'pangolin', 'pdal-c', 'pegtl-2', 'pegtl', 'pe-parse', 'pfring', 'paho-mqttpp3', 'parsi', 'parallelstl', 'phnt',
     'physac', 'pixel', 'plibsys', 'physx', 'pmp-library', 'pmdk', 'pocketpy', 'poissonrecon', 'polyhook2', 'ponder',
     'poolstl', 'portable-snippets', 'popsift', 'portmidi', 'ppconsul', 'ppmagic', 'pravila00-enum-string',
     'pravila00-make-vector', 'projectm', 'promise-cpp', 'projectm-eval', 'proxsuite', 'ptc-print', 'pulsar-client-cpp',
     'qlementine', 'qlementine-icons', 'python3', 'qmex', 'qnnpack', 'qpid-proton', 'pulzed-mini', 'qtkeychain',
     'qtkeychain-qt6', 'qwtw', 'quadtree', 'rabit', 'raygui', 'rbdl-orb', 'readline-win32', 'range-v3-vs2015', 'rbdl',
     'realsense2', 'realm-core', 'recycle', 'recast', 'red0124-ssp', 'refprop-headers', 'rest-rpc', 'restc-cpp',
     'rendergraph', 'resultlib', 'rexo', 'rhash', 'rhasheq', 'riffcpp', 'rioki-glow', 'ripper37-libbase', 'rivers',
     'rlottie', 'rmlui', 'rmqcpp', 'robin-map', 'rsasynccpp', 'robotraconteur-companion', 'rsig', 'rsm-binary-io',
     'rkcommon', 'rsm-bsa', 'rsm-mmio', 'rsocket', 'rtmfp-cpp', 'ruapu', 'rtaudio', 'rxqt', 'ryml', 'safetyhook',
     'sciplot', 'sciter', 'scope-guard', 'scottt-debugbreak', 'sdflib', 'sdl2-image', 'sdl2-mixer', 'sdl2-net',
     'sdl3-image', 'sdl3-ttf', 'selene', 'seacas', 'secp256k1', 'septag-dmon', 'sese', 'sentencepiece', 'sfsexp',
     'seal', 'sfgui', 'shaderwriter', 'shiftmedia-libgcrypt', 'shiftmedia-libgnutls', 'sigmatch', 'simple-fft',
     'shogun', 'shiftmedia-libgpg-error', 'shader-slang', 'simage', 'simpleini', 'simsimd', 'simpleble', 'sltbench',
     'slikenet', 'skcrypter', 'small-gicp', 'sjpeg', 'soapysdr', 'sockpp', 'soem', 'soil', 'sparsehash', 'soil2',
     'soqt', 'spatial-hash', 'spimpl', 'spdk-isal', 'spine-runtimes', 'spirv-reflect', 'spirit-po', 'sprout', 'spout2',
     'sqlite-modern-cpp', 'srpc', 'sse2neon', 'sqlpp11-connector-mysql', 'staticjson', 'stdexec', 'str-view',
     'steam-audio', 'string-theory', 'strtk', 'stronk', 'swenson-sort', 'tacopie', 'superlu', 'tanakh-cmdline',
     'task-thread-pool', 'tcp-pubsub', 'tdscpp', 'telnetpp', 'tgbot-cpp', 'tfhe', 'tensorflow-cc', 'tevclient',
     'tensorflow-common', 'think-cell-range', 'thomasmonkman-filewatch', 'tinyorm', 'tomsolver', 'tinyproto',
     'tree-similarity', 'tree-sitter-cli', 'triton', 'torch-th', 'treehh', 'try-catcher', 'tvision', 'type-lite',
     'turbobase64', 'unicorn-lib', 'ucoro', 'unittest-cpp', 'unimail-cpp-sdk', 'ttauri', 'upa-url', 'umock-c',
     'utf8-range', 'usearch', 'value-ptr-lite', 'uthenticode', 'utfz', 'vcpkg-tool-bazel', 'vcpkg-tool-castxml',
     'vcpkg-tool-lessmsi', 'uvatlas', 'veigar', 'verdict', 'vcpkg-tool-meson', 'vili', 'via-httplib', 'vit-vit-ctpl',
     'vkfft', 'vlpp', 'vladimirshaleev-ipaddress', 'vmaware-vm-detection', 'vsgimgui', 'vsgxchange', 'vs-yasm',
     'vowpal-wabbit', 'vtk-dicom', 'vulkan-memory-allocator-hpp', 'vulkan-tools', 'vulkan-extensionlayer',
     'vulkan-utility-libraries', 'wavelib', 'wabt', 'wangle', 'wepoll', 'webui', 'webthing-cpp', 'wg21-sg14', 'wiiuse',
     'winlamb', 'wmipp', 'wolf-midi', 'wren', 'workflow', 'wxchartdir', 'x86-simd-sort', 'wpilib', 'xframe',
     'xtensor-blas', 'xeus', 'xtensor-fftw', 'xtensor-io', 'yalantinglibs', 'z4kn4fein-semver', 'zeroc-ice', 'zkpp',
     'zlmediakit', 'yasm-tool-helper', 'zserge-webview', 'zookeeper', 'ztd-encoding-tables', 'ztd-idk', 'ztd-platform',
     'ztd-text', 'zycore', 'aaplus', 'accellera-uvm-systemc', 'ztd-static-containers', 'android-ndk', 'angelscript',
     'antlr4', 'argtable2', 'archicad-apidevkit', 'arrow', 'armadillo', 'at-spi2-core', 'at-spi2-atk', 'autoconf',
     'autoconf-archive', 'baical-p7', 'basu', 'automake', 'bazel', 'binutils', 'bigint', 'bison', 'chef-fun', 'bliss',
     'blaze', 'boostdep', 'bzip2', 'cairomm', 'cairo', 'chipmunk2d', 'ccfits', 'cfitsio', 'clhep', 'cigi-ccl',
     'clipper', 'calceph', 'coin-lemon', 'cmocka', 'cppunit', 'cryptopp-pem', 'eigen', 'cspice', 'crashpad', 'cpython',
     'cunit', 'dav1d', 'dbus', 'dependencies', 'depot_tools', 'editline', 'elfutils', 'ensmallen',
     'extra-cmake-modules', 'fftw', 'fmi1', 'fontconfig', 'freetype', 'freexl', 'frugen', 'ftjam', 'geotrans', 'gdbm',
     'getdns', 'gfortran', 'glpk', 'glshaderpp', 'glibmm', 'gnu-config', 'gnulib', 'gnutls', 'gperf',
     'gobject-introspection', 'gst-plugins-bad', 'gst-libav', 'gst-plugins-base', 'gtk-doc-stub', 'gst-plugins-good',
     'half', 'lely-core', 'gst-plugins-ugly', 'libaec', 'hdf4', 'hello-conan', 'libattr', 'libboxes', 'i2c-tools',
     'irrxml', 'imake', 'kmod', 'lemon', 'libaio', 'kuliya', 'libaom-av1', 'libbsd', 'libcap', 'libdatrie',
     'libgettext', 'libdb', 'libdc1394', 'libdisplay-info', 'libdisasm', 'libdrm', 'libelf', 'libevdev', 'libev',
     'libfdk_aac', 'libgpiod', 'libgpg-error', 'libglvnd', 'libgta', 'libiberty', 'libiconv', 'libidn', 'libidn2',
     'libjpeg', 'libliftoff', 'liblzf', 'liblqr', 'libmad', 'libmd', 'libmnl', 'libmicrohttpd', 'libmemcached',
     'libmp3lame', 'libmount', 'libmysqlclient', 'libnfnetlink', 'libnetfilter_queue', 'libnova',
     'libnetfilter_conntrack', 'libnice', 'librttopo', 'liboping', 'libnftnl', 'libpfm4', 'libpciaccess', 'libpq',
     'librasterlite2', 'librasterlite', 'libssh', 'libsvtav1', 'librealsense', 'librhash', 'libseat', 'libsecret',
     'libselinux', 'libsmacker', 'libsndio', 'libspatialite', 'libsquish', 'libtar', 'libunistring', 'libudev',
     'libtasn1', 'libuuid', 'libx264', 'libvdpau', 'libxft', 'libxpm', 'libyuv', 'libxshmfence',
     'linux-syscall-support', 'linux-headers-generic', 'log4cpp', 'luple', 'mocknetworkaccessmanager', 'lzip',
     'mariadb-connector-c', 'maven', 'mesa-glu', 'mawk', 'metal-cpp', 'mingw-builds', 'mpfr', 'mozilla-build',
     'mpdecimal', 'mtdev', 'mysql-connector-c', 'nasm', 'nettle', 'newmat', 'nmea', 'nspr', 'npcap',
     'objectbox-generator', 'odbc', 'openal', 'opencore-amr', 'ohpipeline', 'openapi-generator', 'openfst', 'opengl',
     'opengrm', 'openmesh', 'openjdk', 'openmpi', 'openpam', 'optimlib', 'pangomm', 'panzi-portable-endian', 'pdfium',
     'pffft', 'pexports', 'pixman', 'platform.interfaces', 'pngpp', 'poppler', 'poppler-data', 'pthreads4w',
     'qcustomplot', 'qtxlsxwriter', 'ragel', 'qdbm', 'rapidxml', 'readosm', 'readline', 'rectanglebinpack', 'rply',
     'scdoc', 'scons', 'sdl_mixer', 'serd', 'serf', 'simple-websocket-server', 'soxr', 'soundtouch', 'sqlite3', 'sofa',
     'strawberryperl', 'subunit', 'svgwrite', 'systemc-cci', 'tcp-wrappers', 'szip', 'termcap', 'theora', 'tinyxml',
     'tinkerforge-bindings', 'tllist', 'tqdm-cpp', 'tsil', 'tweetnacl', 'wilzegers-autotest', 'util-linux-libuuid',
     'vaapi', 'vdpau', 'vo-amrwbenc', 'voropp', 'xorg', 'wasmer', 'xorg-gccmakedep', 'wasmedge', 'xorg-makedepend',
     'xorg-proto', 'wasmtime', 'wayland-protocols', 'wineditline', 'xapian-core', 'xkeyboard-config', 'xkbcommon',
     'xorg-macros', 'xorg-cf-files', 'xqilla', 'liblivemedia', 'xz_utils', 'zookeeper-client-c', 'zserio',
     'zulu-openjdk', 'libgdchart-gd', 'xtrans', 'xpresent', 'xulrunner', 'libnspr', 'iptables', 'jbig-kit', 'celt',
     'opkg', 'mesa_demos', 'osip', 'libeigen', 'exosip', 'liborc', 'qcacld', 'neptune', 'gawk', 'dalvik', 'e2fsprogs',
     'tinycompress', 'libaom', 'gsid', 'gdisk', 'f2fs-tools', 'tcf_agent', 'traceroute', 'dnsmasq', 'mtd-utils',
     'findutils', 'bridge-utils', 'ebtables', 'conntrack-tools', 'BusyBox', 'libresolv', 'minidlna', 'cryptsetup',
     'ethtool', 'wget', 'lvm2', 'libogg', 'ofono', 'bash', 'liblog', 'audio_route', 'shared-mime-info', 'x264',
     'libplacebo', 'firefox-esr', 'ogl-runtime', 'android-external-protobuf', 'libbluray', 'net-tools',
     'r-bioc-rhtslib', 'libestr', 'libsoil', 'oddjob', 'spin', 'subread', 'gnome-calls', 'ampr-ripd', 'pngcheck',
     'xloadimage', 'zenity', 'libfontenc', 'libmath-vector-real-xs-perl', 'package-update-indicator', 'bijiben',
     'xmount', 'ephoto', 'liblscp', 'phodav', 'wofi', 'adcli', 'ries', 'talloc', 'wmmisc', 'tcptrace', 'wmtop',
     'libgnt', 'pmars', 'xserver-xorg-video-amdgpu', 'drm-info', 'jikespg', 'nautilus', 'foma', 'musl', 'parted',
     'upower', 'procps-ng', 'keyutils', 'autogen', 'connman', 'v4l-utils', 'nano', 'gnokii', 'berkeleydb', 'ipset',
     'lzo2', 'gnome', 'libtirpc', 'rpcbind', 'lwip', 'sshpass', 'nfs-utils', 'claws-mail', 'sysklogd', 'grub', 'gpgme',
     'knot-dns', 'gnash', 'blender', 'dhcp', 'gif2png', 'cgit', 'grep', 'exempi', 'libwpd', 'kexec-tools', 'xfsprogs',
     'game-music-emu', 'screen', 'hylafax', 'rtmpdump', 'inkscape', 'sylpheed', 'icoutils', 'ghostscript', 'ngircd',
     'bacula', 'man-db', 'terminology', 'vino', 'systemtap', 'samba', 'tftp-hpa', 'dvipng', 'libmms', 'aspell',
     'notmuch', 'mailutils', 'hostapd', 'libcacard', 'classpath', 'sane-backends', 'block_class', 'policycoreutils',
     '389_directory_server', 'spice', 'xdg-utils', 'dbus-glib', 'bogofilter', 'libxt', 'socat', 'libxvmc', 'polkit',
     'patch', 'radius', 'x.org-xserver', 'libmcrypt', 'acpid', 'libxcb', 'emacs', 'libxv', 'libxtst', 'qmail',
     'virglrenderer', 'libxp', 'gzip', 'lasso', 'libxi', 'apparmor', 'pam_ssh', 'qemu-kvm', 'autofs', 'libextractor',
     'gpicview', 'libfs', 'libgig', 'rkit', 'kio-extras', 'libxrender', 'pspp', 'dracut', 'pacman', 'guile', 'realmd',
     'bsd_mailx', 'gdm3', 'cifs-utils', 'urbackup', 'libgwenhywfar', 'libsepol', 'libhx', 'gtkradiant', 'lede',
     'libuser', 'xymon', 'netcf', 'foo2zjs', 'tinysvcmdns', 'janus-proxy', 'seamonkey', 'getmail', 'zendto', '4images',
     'xampp', 'exactimage', 'octopus_deploy', 'fudforum', 'tcexam', 'openvas_manager', 'streaming_media', 'splunk',
     'atmail', 'dotnetnuke', 'contao_cms', 'mdaemon', 'xwiki', 'tinywebgallery', 'avast_antivirus', 'irfanview',
     'rancher', 'ispconfig', 'xnview', 'thttpd', 'twiki', 'nextgen_gallery', 'posh', 'git_for_windows', 'attachecase',
     'resourcespace', 'vbulletin', 'support_incident_tracker', 'wampserver', 'dedecms', 'sugarcrm', 'wps_office',
     'participants_database', 'nexus', 'cs-cart', 'phplist', 'eshop', 'winrar', 'zarafa', 'bozohttpd',
     'simple_machines_forum', 'gazie', 'oscommerce', 'popup_maker', 'websitebaker', 'webkitgtk%2b',
     'unified_infrastructure_management', 'rocket.chat', 'serendipity', 'zenoss', 'glfusion', 'spiceworks',
     'lansweeper', 'usermin', 'searchblox', 'groupwise', 'empirecms', 'contact_form_to_db', 'opensis', 'redcap', 'sasl',
     'batavi', 'linux_diskquota', 'webid', 'boltwire', 'pie-register', 'blogengine.net', 'puppet_agent', 'nomachine',
     'seo_panel', 'zurmo_crm', 'activeperl', 'church_admin', 'pandora_fms', 'wp_booking_system', 'nagios_xi',
     'web_studio', 'wikindx', 'zenphoto', 'spamtitan', 'vxworks', 'ui_for_asp.net_ajax', 'usersultra', 'prestashop',
     'codoforum', 'phpliteadmin', 'navigate', 'vtiger_crm', 'openkm', 'ninja_forms', 'xlpd', 'software-properties',
     'backupguard', 'wallacepos', 's-cms', 'api_manager', 'restws', 'rtfm', 'newstatpress', 'orangehrm', 'livezilla',
     'alpine_linux', 'clansphere', 'huge-it_image_gallery', 'i-doit', 'pixelpost', 'spiffy', 'sphider',
     'twitter_button', 'bitweaver', 'acpid2', 'zoph', 'greenbone_os', 'relevanssi', 'network_audio_system', 'backwpup',
     'open-audit', 'xcloner', 'nextcloud', 'dolphin', 'seeddms', 'konakart', '6kbbs', 'contact_form_7', 'metinfo',
     'gitlab-shell', 'keepass', 'puppet_dashboard', 'feedwordpress', 'apng2gif', 'tiny_tiny_rss', 'magmi',
     'profile_builder', 'kde_applications', 'openam', 'spagobi', 'filemaker_pro_advanced', 'perltidy',
     'java_system_application_server', 'avg_anti-virus', 'nexpose', 'powerchute', 'flexnet_publisher', 'extplorer',
     'xiuno_bbs', 'filemaker_pro', 'wp_support_plus_responsive_ticket_system', 'easy_appointments', 'bosh',
     'apache2triad', 'anti-virus', 'codesys', 'job_manager', 'contact_form', 'eramba', 'cabextract', 'phpwind',
     'acontent', 'quick.cms', 'admidio', 'rompager', 'a-blog_cms', 'socialengine', 'doorgets_cms', 'webaccess',
     'social_buttons_pack', 'leanote', 'xoonips', 'playsms', 'magento', 'advanced_real_estate_script', 'video_gallery',
     'sync', 'xfig', 'mambo_cms', 'yawpp', 'discuzx', 'restaurant_management_system', 'articlefr', 'netkit',
     'libgssglue', 'appointment_booking_calendar', 'google_analyticator', 'magnolia_cms', 'webfs', 'testimonial_slider',
     'weborf_http_server', 'elabftw', 'centos_web_panel', 'alfresco', 'ftpdmin', 'mail-masta_plugin', 'promobar',
     'clean_login', 'xajax', 'core_ftp', 'micro_httpd', 'joyplus-cms', 'linkedin', 'frappe', 'bonita_bpm_portal',
     'minicms', 'internet_download_manager', 'wbce_cms', 'webmail_pro', 'phpfk', 'ftpgetter', 'kentico_cms', 'mp3gain',
     'htaccess', 'peel_shopping', 'jimtawl', 'syscp', 'bludit', 'acymailing_starter', 'contact_form_multi',
     'squidguard', 'wp-members', 'quick.cart', 'asp.net_webforms_report_viewer', 'quotes_and_tips',
     'hospital_management_system', 'pexip_infinity', 'booking_calendar', 'broken_link_checker',
     'nexus_repository_manager', 'mailbird', 'all_in_one_seo_pack', 'discuz%21', 'umip', 'commsy', 'custom_admin_page',
     'powerpress_podcasting', 'raygun4wp', 'mtouch_quiz', 'laravel', 'eyesofnetwork', 'identity_server', 'pluxml',
     'pydio', 'nfsen', 'smooth_slider', 'kunena', 'plib', 'shutter', 'pyftpd', 'helpdezk', 'unrar-free', 'nonecms',
     'smartcms', 'webtitan', 'formalms', 'invoiceplane', 'updraftplus', 'shortcodes_ultimate', 'super', 'open-school',
     'timidity%2b%2b', 'snort_package', 'wp_all_import', 'limit_attempts', 'wuzhicms', 'sysaid', 'suricata_package',
     'trend_micro_antivirus', 'phpmychat_plus', 'evernote', 'total_cache', 'qdpm', 'flexpaper', 'ziproxy',
     'arj_archiver', 'phpmywind', 'enterprise_integrator', 'rzip', 'error_log_viewer', 'showbiz_pro', 'soplanning',
     'xnbd', 'subscriber', 'chess', 'otcms', 'zzcms', 'dmg2img', 'btrbk', 'atftp', 'drupal7', 'firegpg', 'containerd',
     'fig2dev', 'freedroidrpg', 'getmail4', 'gitea', 'giftrans', 'gosa', 'gocr', 'haserl', 'hoteldruid', 'kcron',
     'kimageformats', 'freenet', 'kopanocore', 'libiec61883', 'libemf', 'libgetdata', 'libkiwix', 'libmatio', 'liblip',
     'libpano13', 'liboggz', 'libntlm', 'libpodofo', 'libsdl2', 'libspiro', 'makepasswd', 'libxfcegui4',
     'mysecureshell', 'openjpeg2', 'openldap2', 'partitionmanager', 'minetest', 'pcf2bdf', 'pglogical', 'raptor2',
     'pjproject', 'roundcube', 'sqliteodbc', 'rustc', 'sysdig', 'termpkg', 'totd', 'tintin++', 'v86d', 'xmlstarlet',
     'uronode', 'yabasic', 'zangband', 'zipios++', 'libslirp', 'ableton', 'ableton-link', 'advobfuscator', 'ada-url',
     'activemq-cpp', 'alac-decoder', 'allegro5', 'alsa', 'amd-adl-sdk', 'anari', 'apache-datasketches', 'argagg',
     'arrow-adbc', 'asiosdk', 'atkmm', 'atlmfc', 'autodock-vina', 'avisynthplus', 'beast', 'babl', 'better-enums',
     'bfgroup-lyra', 'bext-text', 'binn', 'bext-mp', 'blas', 'binlog', 'blpapi', 'azure-macro-utils-c',
     'boost-accumulators', 'boost-align', 'boost-algorithm', 'blingfire', 'boost-any', 'boost-asio', 'boost-array',
     'boost-assert', 'boost-assign', 'boost-atomic', 'boost-beast', 'boost-callable-traits', 'boost-charconv',
     'boost-bimap', 'boost-cobalt', 'boost-chrono', 'boost-circular-buffer', 'boost-compute', 'boost-bind',
     'boost-compat', 'boost-config', 'boost-concept-check', 'boost-container', 'boost-container-hash', 'boost-context',
     'boost-contract', 'boost-core', 'boost-coroutine', 'boost-coroutine2', 'boost-conversion', 'boost-convert',
     'boost-date-time', 'boost-describe', 'boost-crc', 'boost-dll', 'boost-dynamic-bitset', 'boost-detail',
     'boost-endian', 'boost-exception', 'boost-filesystem', 'boost-fiber', 'boost-foreach', 'boost-format',
     'boost-function', 'boost-flyweight', 'boost-function-types', 'boost-fusion', 'boost-geometry', 'boost-graph',
     'boost-gil', 'boost-functional', 'boost-hana', 'boost-headers', 'boost-graph-parallel', 'boost-histogram',
     'boost-hof', 'boost-heap', 'boost-integer', 'boost-hash2', 'boost-interprocess', 'boost-icl', 'boost-iostreams',
     'boost-intrusive', 'boost-iterator', 'boost-json', 'boost-interval', 'boost-io', 'boost-lambda2',
     'boost-lexical-cast', 'boost-lambda', 'boost-locale', 'boost-lockfree', 'boost-log', 'boost-math', 'boost-logic',
     'boost-metaparse', 'boost-local-function', 'boost-move', 'boost-mp11', 'boost-mpi', 'boost-mpl',
     'boost-multi-array', 'boost-mysql', 'boost-multiprecision', 'boost-multi-index', 'boost-mqtt5', 'boost-nowide',
     'boost-msm', 'boost-optional', 'boost-numeric-conversion', 'boost-outcome', 'boost-odeint', 'boost-parameter',
     'boost-pfr', 'boost-phoenix', 'boost-parameter-python', 'boost-parser', 'boost-polygon', 'boost-poly-collection',
     'boost-predef', 'boost-process', 'boost-pool', 'boost-program-options', 'boost-preprocessor', 'boost-property-map',
     'boost-python', 'boost-property-tree', 'boost-proto', 'boost-random', 'boost-qvm', 'boost-property-map-parallel',
     'boost-range', 'boost-ptr-container', 'boost-rational', 'boost-ratio', 'boost-regex', 'boost-safe-numerics',
     'boost-redis', 'boost-scope-exit', 'boost-serialization', 'boost-signals2', 'boost-smart-ptr', 'boost-scope',
     'boost-sort', 'boost-spirit', 'boost-stacktrace', 'boost-static-assert', 'boost-statechart', 'boost-static-string',
     'boost-system', 'boost-test', 'boost-thread', 'boost-throw-exception', 'boost-stl-interfaces', 'boost-tti',
     'boost-type-erasure', 'boost-tuple', 'boost-timer', 'boost-type-index', 'boost-type-traits', 'boost-typeof',
     'boost-tokenizer', 'boost-ublas', 'boost-units', 'boost-url', 'boost-unordered', 'boost-utility', 'boost-uuid',
     'boost-variant', 'boost-uninstall', 'boost-variant2', 'boost-vmd', 'boost-winapi', 'boost-xpressive', 'boost-yap',
     'boost-wave', 'brunocodutra-metal', 'clap-cleveraudio', 'casadi', 'casclib', 'catch', 'cblas', 'cello', 'chartdir',
     'cgicc', 'chromium-base', 'chronoengine', 'clapack', 'coin-or-clp', 'coin-or-buildtools', 'clblas', 'colmap',
     'coin-or-osi', 'comms-ublox', 'comms', 'commsdsl', 'configcat', 'cpp-peglib', 'cppfs', 'cppxaml', 'crashrpt',
     'crfsuite', 'cpp-exiftool', 'cppslippi', 'curlcpp', 'cuda', 'd3d12-memory-allocator', 'cudnn', 'cutelyst2',
     'darts-clone', 'dartsim', 'd3dx12', 'dv-processing', 'devicenameresolver', 'discord-game-sdk', 'edflib',
     'directx12-agility', 'distorm', 'discordcoreapi', 'dbghelp', 'docopt', 'directxsdk', 'ecal', 'dstorage', 'eigen3',
     'eipscanner', 'esaxx', 'elements', 'ezfoundation', 'dxsdk-d3dx', 'fadbad', 'fastcgi', 'font-util', 'fdlibm',
     'fftw3', 'faudio', 'fbgemm', 'fins', 'fftwpp', 'fmem', 'fastfeat', 'fmilib', 'gameinput', 'gmsh', 'getopt-win32',
     'gamedev-framework', 'getopt', 'gettimeofday', 'gexiv2', 'gherkin-c', 'gl2ps', 'gettext-libintl',
     'glib-networking', 'google-cloud-cpp-common', 'gst-rtsp-server', 'gsasl', 'google-cloud-cpp-spanner', 'gtkmm',
     'gtk3', 'gumbo', 'gul14', 'gz-cmake', 'gz-common', 'gz-fuel-tools', 'gz-cmake3', 'gz-gui', 'gz-fuel-tools8',
     'gz-common5', 'gz-gui7', 'gz-math', 'gz-msgs', 'gz-math7', 'gz-msgs9', 'gz-physics6', 'gz-plugin2', 'gz-physics',
     'gz-plugin', 'gz-rendering', 'gz-rendering7', 'gz-sim', 'gz-sensors7', 'gz-sensors', 'gz-tools2', 'gz-transport',
     'gz-tools', 'gz-transport12', 'gz-utils', 'gz-utils2', 'hashids', 'ignition-modularscripts', 'hello-imgui',
     'healpix', 'imcce-openfa', 'hjson-cpp', 'hungarian', 'hypre', 'idevicerestore', 'ideviceinstaller', 'igloo',
     'igraph', 'iausofa', 'intel-ipsec', 'ijg-libjpeg', 'irrlicht', 'intelrdfpmathlib', 'io2d', 'itpp', 'irsdkcpp',
     'jack2', 'intel-mkl', 'jkqtplotter', 'json-spirit', 'json-glib', 'kddockwidgets', 'kdsoap', 'json11', 'kenlm',
     'kf5archive', 'kf5attica', 'kf5auth', 'kf5bookmarks', 'kf5codecs', 'kf5config', 'kf5configwidgets',
     'kf5completion', 'kf5crash', 'kf5coreaddons', 'kf5dbusaddons', 'kf5declarative', 'kf5globalaccel', 'kf5i18n',
     'kf5guiaddons', 'kf5diagram', 'kf5holidays', 'kf5jobwidgets', 'kf5iconthemes', 'kf5itemviews', 'kf5itemmodels',
     'kf5kcmutils', 'kf5kio', 'kf5notifications', 'kf5package', 'kf5newstuff', 'kf5parts', 'kf5service', 'kf5solid',
     'kinectsdk1', 'kf5sonnet', 'kf5textwidgets', 'kf5plotting', 'kf5texteditor', 'kf5xmlgui', 'kf5wallet',
     'kf5widgetsaddons', 'klein', 'kf5windowsystem', 'kinectsdk2', 'lapack-reference', 'lapack', 'kwsys',
     'lemon-parser-generator', 'libcamera', 'libcaer', 'levmar', 'lensfun', 'libadwaita', 'libaiff', 'libaaplus',
     'libassuan', 'libalkimia', 'libbf', 'libcerf', 'libcanberra', 'libcpplocate', 'libcurl-simple-https', 'libdmx',
     'libdvdcss', 'libdshowcapture', 'libdvdnav', 'libe57', 'libdvdread', 'libedit', 'libftdi', 'libfido2', 'libftdi1',
     'libgme', 'libice', 'libgnutls', 'libideviceactivation', 'libimobiledevice-glue', 'libirecovery', 'liblbfgs',
     'liblzma', 'liblttng-ust', 'libmpeg2', 'libmypaint', 'libmodman', 'liblemon', 'libodb', 'libodb-boost',
     'libodb-mysql', 'libodb-pgsql', 'libnice-gst', 'libodb-sqlite', 'libopensp', 'liborigin', 'librtpi', 'liboqs',
     'libosmscout', 'libosmium', 'libosip2', 'libp7-baical', 'libpopt', 'libredwg', 'librtmp', 'libsigcpp',
     'libp7client', 'libsigcpp-3', 'libsm', 'libsoundio', 'libstemmer', 'libstk', 'libsnoretoast', 'libtorch',
     'libu2f-server', 'libusb-win32', 'libxau', 'liburcu', 'libxaw', 'libxcomposite', 'libx11', 'libxcvt', 'libxdamage',
     'libxfixes', 'libxdmcp', 'libxdf', 'libxinerama', 'libxkbcommon', 'libxkbfile', 'libxmu', 'libxpresent', 'libxmp',
     'libxres', 'libxscrnsaver', 'libxxf86vm', 'lightningscanner', 'lpeg', 'llvm', 'lodepng-c', 'magma',
     'log4cpp-log4cpp', 'makeid', 'lilv', 'mathgl', 'marble', 'matplotplusplus', 'meschach', 'mhook', 'micro-gl',
     'mmloader', 'monkeys-audio', 'mp-units', 'moos-core', 'moos-essential', 'mp3lame', 'moos-ui', 'ms-angle',
     'msgpack11', 'ms-gdk', 'ms-gdkx', 'mypaint-brushes', 'mygui', 'nanoarrow', 'nanobind', 'msmpi', 'nccl', 'netgen',
     'mujoco', 'ngspice', 'nonius', 'node-api-headers', 'nuspell', 'networkdirect-sdk', 'ntf-core', 'oatpp-mbedtls',
     'octave', 'omniorb', 'omplapp', 'openctm', 'openmvs', 'opentracing', 'openscap', 'openvpn3', 'openturns',
     'oscpack', 'optional-bare', 'osg-qt', 'plasma-wayland-protocols', 'paraview', 'parmetis', 'parquet', 'pciids',
     'pfultz2-linq', 'pdal-dimbuilder', 'pipewire', 'plf-hive', 'plplot', 'pngwriter', 'plustache', 'portaudio',
     'portsmf', 'pravila00-enumflag', 'presentmon', 'pthread', 'pthread-stubs', 'polyclipping', 'pthreads', 'ptyqt',
     'qhttpengine', 'python2', 'qscintilla', 'qt3d', 'qt5-3d', 'qt5-canvas3d', 'qt5-base', 'qt5-charts',
     'qt5-connectivity', 'qt5-androidextras', 'qt5-activeqt', 'qt5-declarative', 'qt5-datavis3d', 'qt5-gamepad',
     'qt5-doc', 'qt5-graphicaleffects', 'qt5-imageformats', 'qt5-location', 'qt5-multimedia', 'qt5-mqtt',
     'qt5-networkauth', 'qt5-modularscripts', 'qt5-macextras', 'qt5-quickcontrols', 'qt5-quickcontrols2',
     'qt5-purchasing', 'qt5-remoteobjects', 'qt5-quick3d', 'qt5-quicktimeline', 'qt5-scxml', 'qt5-sensors',
     'qt5-script', 'qt5-serialbus', 'qt5-serialport', 'qt5-speech', 'qt5-svg', 'qt5-tools', 'qt5-translations',
     'qt5-webchannel', 'qt5-wayland', 'qt5-virtualkeyboard', 'qt5-webengine', 'qt5-webglplugin', 'qt5-websockets',
     'qt5-webview', 'qt5-x11extras', 'qt5-xmlpatterns', 'qt5-winextras', 'qtactiveqt', 'qtapplicationmanager', 'qtbase',
     'qtcharts', 'qtcoap', 'qt5compat', 'qtconnectivity', 'qtdatavis3d', 'qtdeclarative', 'qtdeviceutilities', 'qtdoc',
     'qthttpserver', 'qtgraphs', 'qtgrpc', 'qtimageformats', 'qtinterfaceframework', 'qtlanguageserver', 'qtlocation',
     'qtlottie', 'qtmqtt', 'qtnetworkauth', 'qtopcua', 'qtmultimedia', 'qtpositioning', 'qtquick3d', 'qtquick3dphysics',
     'qtquicktimeline', 'qtquickeffectmaker', 'qtquickcontrols2', 'qtserialbus', 'qtsensors', 'qtscxml', 'qtserialport',
     'qtremoteobjects', 'qtshadertools', 'qtsvg', 'qtspeech', 'qttools', 'qttranslations', 'qtvirtualkeyboard',
     'qtwebchannel', 'qtwayland', 'qtwebengine', 'qtwebsockets', 'random123', 'qtwebview', 'randomstr', 'rapidobj',
     'rapidxml-ns', 'readline-osx', 'rappture', 'readline-unix', 'rerun-sdk', 'restclient-cpp', 'robotraconteur',
     'rnnoise', 'rtabmap', 'rtabmap-res-tool', 'rtlsdr', 'ruckig', 'scotch', 'rxspencer', 'rubberband', 'sajson',
     'salome-configuration', 'salome-med-fichier', 'salome-medcoupling', 'saucer', 'scylla-wrapper', 'sdformat13',
     'sdformat', 'sdl1', 'sdl1-mixer', 'sciter-js', 'scenepic', 'sdl1-net', 'sfcgal', 'sdl2-gfx', 'sdl2',
     'sdl2-mixer-ext', 'sdl2-ttf', 'sdl2pp', 'sdl3', 'septag-sx', 'seqan', 'sf2cute', 'simonbrunel-qtpromise',
     'sleepy-discord', 'simbody', 'smpeg2', 'snap7', 'solid3', 'spaceland', 'sord', 'spatialite-tools', 'sparsepp',
     'spdk', 'spglib', 'spdk-ipsec', 'spdk-dpdk', 'stackwalker', 'srell', 'stftpitchshift', 'stormlib', 'starlink-ast',
     'strict-variant', 'stxxl', 'suitesparse', 'suitesparse-amd', 'suitesparse-btf', 'suitesparse-ccolamd',
     'suitesparse-cholmod', 'suitesparse-colamd', 'suitesparse-config', 'suitesparse-cxsparse', 'suitesparse-camd',
     'suitesparse-graphblas', 'suitesparse-klu', 'suitesparse-ldl', 'suitesparse-mongoose', 'tiff',
     'suitesparse-lagraph', 'tiny-process-library', 'suitesparse-paru', 'suitesparse-rbio', 'suitesparse-spex',
     'suitesparse-spqr', 'suitesparse-umfpack', 'tap-windows6', 'tgui', 'talib', 'tinkerforge', 'tinyexpr', 'tinyfsm',
     'tinynpy', 'tinythread', 'tinytiff', 'tl-generator', 'tobias-loew-flags', 'tmxparser', 'treehopper', 'triangle',
     'tinyfiledialogs', 'usbmuxd', 'vamp-sdk', 'vcpkg-boost', 'vcpkg-cmake', 'vcpkg-cmake-config',
     'vcpkg-cmake-get-vars', 'vcpkg-gfortran', 'vcpkg-get-python', 'vcpkg-get-python-packages', 'vcpkg-gn',
     'vcpkg-make', 'vcpkg-msbuild', 'vcpkg-pkgconfig-get-modules', 'vcpkg-qmake', 'vcpkg-tool-ninja',
     'vcpkg-tool-mozbuild', 'vcpkg-tool-nodejs', 'vcpkg-tool-gyp-next', 'vlfeat', 'vcpkg-tool-gn', 'vcpkg-tool-python2',
     'vst3sdk', 'vulkan', 'vtk-m', 'vulkan-hpp', 'wampcc', 'wincrypt', 'wcslib', 'vulkan-sdk-components', 'webview2',
     'winpty', 'wintoast', 'winpixevent', 'woff2', 'wolfmqtt', 'winsock2', 'wxcharts', 'wolftpm', 'xapian', 'xbitmaps',
     'xcb-proto', 'x-plane', 'xaudio2redist', 'xcb-util', 'xcb-render-util', 'xcb-keysyms', 'xcb-image',
     'xcb-util-errors', 'xcb-util-m4', 'xcb-util-wm', 'xproto', 'yasm-tool', 'yato', 'zimpl', 'ztd-cuneicode', 'zydis',
     'libinput', 'macchina', 'opentdf-client', 'wayland', 'xcrash', 'coreutils', 'mesa', 'memtester', 'accountsservice',
     'libcroco', 'empathy', 'clutter', 'zarafa_collaboration_platform', 'cherokee', 'libxcursor', 'shadowsocks-libev',
     'chicken', 'lintian', 'tdiary', 'pale_moon', 'libxext', 'libxfont', 'libsmi', 'matrixssl', 'webapp', 'libxrandr',
     'fish', 'spice-vdagent', 'uchardet', 'ecdsautils']


import re
from collections import Counter
from typing import List, Dict
from loguru import logger

class StringFilter:
    def __init__(self,
                 max_copyright: int = 15,  # Maximum number of copyright/license strings
                 max_paths: int = 20,  # Maximum number of path/URL strings
                 max_function_prefixes: int = 15,  # Maximum number of function prefixes
                 max_logs: int = 10,  # Maximum number of log strings
                 max_component_strings: int = 25,  # Maximum number of strings containing component names
                 max_versions: int = 8,  # Maximum number of version strings
                 max_string_length: int = 200,  # Maximum string length
                 max_matches_per_component: int = 10,  # Maximum matches per component
                 debug: bool = False):

        self.max_copyright = max_copyright
        self.max_paths = max_paths
        self.max_function_prefixes = max_function_prefixes
        self.max_logs = max_logs
        self.max_component_strings = max_component_strings
        self.max_versions = max_versions
        self.max_string_length = max_string_length
        self.max_matches_per_component = max_matches_per_component
        self.debug = debug

        # 1. Broad copyright/license patterns - prefer over-inclusion to avoid missing items
        self.copyright_patterns = [
            r'(?i)copyright',  # any occurrence of "copyright"
            r'(?i)©',  # copyright symbol
            r'(?i)\(c\)',  # (c) copyright mark
            r'(?i)license',  # any occurrence of "license"
            r'(?i)licensed',  # licensing related
            r'(?i)permission',  # permission/license grant
            r'(?i)redistribution',  # redistribution
            r'(?i)all rights reserved',  # all rights reserved
            r'(?i)author',  # author info
            r'(?i)maintainer',  # maintainer
            r'(?i)contributor',  # contributor
            r'(?i)written by',  # written by
            r'(?i)created by',  # created by
            r'(?i)developed by',  # developed by
            r'(?i)foundation',  # foundation
            r'(?i)project',  # project
            r'(?i)software',  # software
            r'(?i)library',  # library
            r'(?i)framework',  # framework
            r'(?i)toolkit',  # toolkit
        ]

        # 2. Path/URL patterns - focus on paths likely to contain component info
        self.path_patterns = [
            # Source code related paths - most valuable
            r'/[^/\s]*(?:src|source|include|lib|libs|library|libraries)/[^\s]*',
            r'[^/\s]+/(?:src|source|include|lib|libs)/[^/\s]+',

            # Repository URLs - highly valuable
            r'https?://(?:github|gitlab|bitbucket|sourceforge)\.(?:com|org)/[^\s]+',
            r'git://[^\s]+',
            r'svn://[^\s]+',

            # Paths that may contain library names
            r'/[^/\s]*(?:lib\w+|[a-z]+lib)/[^\s]*',
            r'/usr/(?:lib|include|share)/[^/\s]+/[^\s]*',
            r'/opt/[^/\s]+/[^\s]*',

            # Build and installation paths
            r'/[^/\s]*(?:build|install|cmake|configure)/[^\s]*',
            r'\.\./[^\s]+',  # relative path

            # Windows paths
            r'[A-Z]:\\[^\s]*(?:lib|include|src|source)[^\s]*',

            # Other potentially valuable paths
            r'[^/\s]+\.(?:so|a|dll|dylib)(?:\.[0-9]+)*',  # library file
            r'/[^/\s]*\w+[^/\s]*/[^/\s]*\.(?:h|hpp|c|cpp|py|js)[^\s]*',  # source file
        ]

        # 3. Version info patterns - more precise
        self.version_patterns = [
            r'(?i)version\s+v?(\d+(?:\.\d+){1,3}(?:[._-](?:alpha|beta|rc|dev|pre)\d*)?)',
            r'(?i)v(\d+(?:\.\d+){1,3}(?:[._-](?:alpha|beta|rc|dev|pre)\d*)?)',
            r'\b(\d+(?:\.\d+){2,3}(?:[._-](?:alpha|beta|rc|dev|pre)\d*)?)\b',
            r'(?i)build\s+(\d+)',
            r'(?i)revision\s+(\d+)',
            r'(?i)commit\s+([a-f0-9]{7,})',
            r'(\d{4}[-./]\d{1,2}[-./]\d{1,2})',  # date format
        ]

        # 4. Log keywords
        self.log_keywords = [
            'error', 'warning', 'debug', 'info', 'log', 'failed', 'success',
            'initialize', 'init', 'startup', 'shutdown', 'config', 'loading',
            'unable to', 'cannot', 'failed to', 'successfully'
        ]

        # 5. Known component names list - set via set_known_components
        self.known_component_names = []

        # Precompile regex patterns for performance
        self.component_patterns = {}
        self.component_lib_patterns = {}

        self._compile_patterns()

    def _compile_patterns(self):
        """Precompile regex patterns for performance"""
        self.copyright_compiled_patterns = [re.compile(pattern) for pattern in self.copyright_patterns]
        self.path_compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.path_patterns]
        self.version_compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.version_patterns]

    def _prepare_component_patterns(self):
        """Preprocess component names and create efficient matching structures"""
        if not self.known_component_names:
            self.component_patterns = {}
            self.component_lib_patterns = {}
            return

        self.component_patterns = {}
        self.component_lib_patterns = {}

        # Define separator pattern: spaces, underscores, dots, dashes, slashes, pipes, etc.
        # (?:^|[\s._\-/|\\:;,()[\]{}@#$%^&*+=<>?!~`"']) means start or a separator
        # (?=[\s._\-/|\\:;,()[\]{}@#$%^&*+=<>?!~`"']|$) means followed by a separator or end
        separator_pattern = r'[\s._\-/|\\:;,()[\]{}@#$%^&*+=<>?!~`"\']'

        for component in self.known_component_names:
            component_lower = component.lower()
            try:
                # Create standalone word matching patterns
                # 1. Full standalone word match
                word_pattern = rf'(?:^|{separator_pattern})({re.escape(component_lower)})(?={separator_pattern}|$)'
                self.component_patterns[component] = re.compile(word_pattern, re.IGNORECASE)

                # 2. "lib" prefix match (also standalone)
                lib_pattern = rf'(?:^|{separator_pattern})(lib{re.escape(component_lower)})(?={separator_pattern}|$)'
                self.component_lib_patterns[component] = re.compile(lib_pattern, re.IGNORECASE)

            except re.error as e:
                # Skip if regex compilation fails due to special characters
                if self.debug:
                    logger.warning(f"Failed to compile pattern for component '{component}': {e}")
                continue

    def _is_component_match(self, component: str, string: str) -> bool:
        """
        Check whether the component name appears as a standalone word in the string.
        Supports various separators: spaces, underscores, dots, dashes, slashes, pipes, etc.
        """
        if component not in self.component_patterns and component not in self.component_lib_patterns:
            return False

        # First try full word match
        if component in self.component_patterns:
            if self.component_patterns[component].search(string):
                return True

        # Then try 'lib' prefix match
        if component in self.component_lib_patterns:
            if self.component_lib_patterns[component].search(string):
                return True

        return False

    def _truncate_string(self, s: str) -> str:
        """Truncate overly long strings"""
        return s[:self.max_string_length] if len(s) > self.max_string_length else s

    def _debug_print(self, category: str, items: List[str]):
        """Debug print helper"""
        if self.debug:
            logger.info(f"\n=== {category} ===")
            for i, item in enumerate(items[:5], 1):
                logger.info(f"{i}. {item}")
            if len(items) > 5:
                logger.info(f"... and {len(items) - 5} more")
            logger.info(f"Total: {len(items)}")

    def _debug_print_component_results(self, component_results: Dict[str, List[str]]):
        """Debug print for component match results"""
        if not self.debug:
            return

        logger.info(f"\n=== COMPONENT NAME MATCHES ===")
        total_matches = sum(len(matches) for matches in component_results.values())
        logger.info(f"Found matches for {len(component_results)} components, total {total_matches} strings")

        # Show the first few components with matches
        for i, (component, matches) in enumerate(list(component_results.items())[:5]):
            logger.info(f"{i + 1}. {component} ({len(matches)} matches):")
            for j, match in enumerate(matches[:3]):  # show first 3 matches per component
                logger.info(f"   - {match}")
            if len(matches) > 3:
                logger.info(f"   ... and {len(matches) - 3} more")

    def extract_copyright_license(self, strings: List[str]) -> List[str]:
        """Broadly filter copyright and license information"""
        results = []
        seen = set()

        for string in strings:
            # Basic length filtering
            if not (5 <= len(string) <= self.max_string_length * 2):
                continue

            # Use precompiled patterns
            for pattern in self.copyright_compiled_patterns:
                if pattern.search(string):
                    truncated = self._truncate_string(string)
                    if truncated not in seen:
                        results.append(truncated)
                        seen.add(truncated)
                    break

        # Simple priority: prefer those with year, organization, etc.
        def priority_score(s):
            score = 0
            if re.search(r'(?:19|20)\d{2}', s):  # contains year
                score += 10
            if re.search(r'(?i)(?:inc|ltd|corp|foundation|project)', s):  # contains organization
                score += 5
            if 'copyright' in s.lower():
                score += 3
            return score

        results.sort(key=lambda s: (priority_score(s), s), reverse=True)

        self._debug_print("COPYRIGHT/LICENSE", results[:self.max_copyright])
        return results[:self.max_copyright]

    def extract_paths_urls(self, strings: List[str]) -> List[str]:
        """Filter paths and URLs, focusing on ones containing component information"""
        results = []
        seen = set()

        for string in strings:
            if not (5 <= len(string) <= self.max_string_length * 2):
                continue

            # Use precompiled patterns
            for pattern in self.path_compiled_patterns:
                if pattern.search(string):
                    truncated = self._truncate_string(string)
                    if truncated not in seen:
                        results.append(truncated)
                        seen.add(truncated)
                    break

        # Priority sorting: repository URL > source path > library path > others
        def path_priority(s):
            score = 0
            s_lower = s.lower()

            # Repository URLs have the highest priority
            if any(repo in s_lower for repo in ['github', 'gitlab', 'bitbucket', 'sourceforge']):
                score += 20

            # Source code paths have high priority
            if any(src in s_lower for src in ['src/', 'source/', 'include/']):
                score += 15

            # Library paths have medium priority
            if any(lib in s_lower for lib in ['lib/', 'libs/', 'library/']):
                score += 10

            # Contains library file extension
            if re.search(r'\.(so|a|dll|dylib)', s_lower):
                score += 8

            # Medium length preferred
            if 20 <= len(s) <= 100:
                score += 5

            return score

        results.sort(key=lambda s: (path_priority(s), s), reverse=True)

        self._debug_print("PATHS/URLS", results[:self.max_paths])
        return results[:self.max_paths]

    def extract_function_prefixes(self, strings: List[str]) -> List[str]:
        """Analyze and count function prefixes"""
        function_names = []

        # Extract potential function names
        for string in strings:
            # Simple function names: start with a letter, alnum/underscore, reasonable length
            if (re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', string) and
                    3 <= len(string) <= 50 and
                    not string.isupper()):  # exclude all-uppercase constants
                function_names.append(string)

        # Extract prefixes
        prefixes = []
        for func in function_names:
            if '_' in func:
                # Prefix separated by underscore
                prefix = func.split('_')[0]
                if len(prefix) >= 2:
                    prefixes.append(prefix)
            elif len(func) > 4:
                # CamelCase prefix (simple handling)
                match = re.match(r'^[a-z]+', func)
                if match:
                    prefixes.append(match.group())

        # Count prefix frequency
        prefix_counts = Counter(prefixes)

        # Generate prefix statistics result
        prefix_results = []
        for prefix, count in prefix_counts.most_common():
            if count >= 2:  # Prefix must appear at least twice to be meaningful
                prefix_results.append(f"{prefix} (count: {count})")

        self._debug_print("FUNCTION PREFIXES", prefix_results[:self.max_function_prefixes])
        return prefix_results[:self.max_function_prefixes]

    def extract_log_messages(self, strings: List[str]) -> List[str]:
        """Extract log messages"""
        candidates = []

        for string in strings:
            # Length filtering
            if not (15 <= len(string) <= self.max_string_length):
                continue

            # Check log characteristics
            string_lower = string.lower()
            has_log_keyword = any(keyword in string_lower for keyword in self.log_keywords)
            has_format_specifier = bool(re.search(r'%[sdxofg]', string))
            looks_like_message = bool(re.search(r'[A-Z][a-z]+.*[a-z]', string))

            if has_log_keyword or has_format_specifier or looks_like_message:
                candidates.append(string)

        # Sort by relevance
        def log_relevance(s):
            score = 0
            s_lower = s.lower()
            score += sum(keyword in s_lower for keyword in self.log_keywords) * 3
            if '%' in s:
                score += 2
            if any(word in s_lower for word in ['failed', 'error', 'cannot', 'unable']):
                score += 5
            return score

        candidates.sort(key=lambda s: (log_relevance(s), s), reverse=True)

        # De-duplicate
        unique_candidates = []
        seen = set()
        for candidate in candidates:
            if candidate not in seen:
                unique_candidates.append(candidate)
                seen.add(candidate)

        self._debug_print("LOG MESSAGES", unique_candidates[:self.max_logs])
        return unique_candidates[:self.max_logs]

    def extract_version_info(self, strings: List[str]) -> List[str]:
        """Extract version information"""
        results = []
        seen = set()

        for string in strings:
            if len(string) > self.max_string_length:
                continue

            # Use precompiled patterns
            for pattern in self.version_compiled_patterns:
                if pattern.search(string):
                    truncated = self._truncate_string(string)
                    if truncated not in seen:
                        results.append(truncated)
                        seen.add(truncated)
                    break

        results.sort(key=lambda s: (len(s), s), reverse=True)

        self._debug_print("VERSION INFO", results[:self.max_versions])
        return results[:self.max_versions]

    def extract_component_name_strings(self, strings: List[str]) -> Dict[str, List[str]]:
        """Extract strings containing known component names, return a dict keyed by component"""
        if not self.known_component_names:
            return {}

        # Preprocess strings
        processed_strings = []
        for string in strings:
            if len(string) <= self.max_string_length:
                truncated = self._truncate_string(string)
                processed_strings.append(truncated)

        # Phase 1: Fast filtering - simple containment check
        candidate_components = []
        seen_components = set()
        all_strings_combined = ' '.join(processed_strings).lower()

        if self.debug:
            logger.info(f"Phase 1: Fast filtering from {len(self.known_component_names)} components...")

        for component in sorted(self.known_component_names):  # sorted for determinism
            component_lower = component.lower()
            # Simple containment check
            if (component_lower in all_strings_combined or
                    f"lib{component_lower}" in all_strings_combined):
                if component not in seen_components:
                    candidate_components.append(component)
                    seen_components.add(component)

        if self.debug:
            logger.info(f"Phase 1: Filtered down to {len(candidate_components)} candidate components")

        # Phase 2: Precise matching - standalone word matching for candidate components
        component_results = {component: [] for component in candidate_components}
        string_to_components = {}

        if self.debug:
            logger.info(f"Phase 2: Precise matching for {len(candidate_components)} components...")

        for component in candidate_components:
            for original_string in processed_strings:
                # Use precise standalone word matching
                if self._is_component_match(component, original_string):
                    component_results[component].append(original_string)
                    if original_string not in string_to_components:
                        string_to_components[original_string] = []
                    string_to_components[original_string].append(component)

        # Remove components without matches
        component_results = {k: v for k, v in component_results.items() if v}

        # For each component, de-duplicate, sort, and limit the number of matches
        for component in sorted(component_results.keys()):  # sorted for determinism
            # De-duplicate
            unique_matches = list(dict.fromkeys(component_results[component]))
            # Sort
            component_results[component] = self._sort_component_matches(
                unique_matches, string_to_components
            )
            # Limit the number of matches per component
            component_results[component] = component_results[component][:self.max_matches_per_component]

        if self.debug:
            self._debug_print_component_results(component_results)

        return component_results

    def _sort_component_matches(self, matches: List[str], string_to_components: Dict[str, List[str]]) -> List[str]:
        """Sort component match results"""

        def priority_score(s):
            score = 0
            matched_comps = string_to_components.get(s, [])

            # More matched components => higher priority
            score += len(matched_comps) * 10

            # Prefer strings containing copyright or version info
            s_lower = s.lower()
            if any(kw in s_lower for kw in ['copyright', 'version', 'license']):
                score += 15

            # Prefer path-like strings
            if '/' in s or '\\' in s or 'http' in s_lower:
                score += 10

            # Prefer medium length
            if 10 <= len(s) <= 80:
                score += 5

            return score

        return sorted(matches, key=lambda s: (priority_score(s), s), reverse=True)

    def set_known_components(self, component_names: List[str]):
        """Set known component names list"""
        self.known_component_names = sorted(component_names)  # sorted for determinism
        self._prepare_component_patterns()
        if self.debug:
            logger.info(f"Set {len(component_names)} known component names")

    def filter_strings(self, strings: List[str]) -> Dict[str, any]:
        """Main string filtering method"""
        if self.debug:
            logger.info(f"Processing {len(strings)} strings...")

        result = {
            'license_copyright': self.extract_copyright_license(strings),
            'paths_urls': self.extract_paths_urls(strings),
            'function_prefixes': self.extract_function_prefixes(strings),
            'log_messages': self.extract_log_messages(strings),
            'version_info': self.extract_version_info(strings),
            'component_matches': self.extract_component_name_strings(strings),  # now returns a dict
        }

        if self.debug:
            component_count = len(result['component_matches']) if isinstance(result['component_matches'], dict) else 0
            other_count = sum(
                len(v) if isinstance(v, list) else 0 for k, v in result.items() if k != 'component_matches')
            logger.info(f"Total: {other_count} filtered strings + {component_count} component types matched")

        return result


# Usage example
if __name__ == "__main__":
    # Create filter instance
    filter_instance = StringFilter(debug=True)

    # Set known components (example)
    known_components = ['openssl', 'zlib', 'curl', 'boost', 'opencv', 'ssl', 'json']
    filter_instance.set_known_components(known_components)

    # Test strings - include various cases
    test_strings = [
        "Copyright 2023 OpenSSL Foundation",  # should match openssl
        "/usr/lib/libssl.so.1.1",  # should match ssl
        "https://github.com/openssl/openssl",  # should match openssl
        "version 1.1.1",
        "ssl_init_library",  # should match ssl
        "ssl-connect-failed",  # should match ssl
        "ERROR: unable to load certificate",
        "zlib compression library",  # should match zlib
        "boost::algorithm::split",  # should match boost
        "opencv_core",  # should match opencv
        "opensslconfig",  # should NOT match openssl (not a standalone word)
        "lib/openssl/include",  # should match openssl
        "parse_json_data",  # should match json
        "jsonparser",  # should NOT match json (not a standalone word)
        "config.json",  # should match json
        "SSL_CTX_new",  # should match ssl (case-insensitive)
        "OPENSSL_VERSION",  # should match openssl (case-insensitive)
    ]

    # Execute filtering
    results = filter_instance.filter_strings(test_strings)

    # Output results
    print("\n=== FINAL RESULTS ===")
    for category, items in results.items():
        if category == 'component_matches':
            print(f"\n{category.upper()}:")
            for component, matches in items.items():
                print(f"  {component}: {matches}")
        else:
            print(f"\n{category.upper()}: {items}")