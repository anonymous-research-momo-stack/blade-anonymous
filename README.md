# BSCA Expert Agent API

二进制软件成分分析专家代理API

## 项目简介

这是一个基于FastAPI的二进制软件成分分析专家代理API，用于分析二进制文件中的组件、漏洞和风险。

## 功能模块

1. **组件匹配模块** - 识别二进制文件中的软件组件
2. **Agent分析模块** - 智能分析二进制文件
3. **Workflow模块** - 工作流程管理
4. **评估模块** - 风险评估和报告

## 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 运行应用

```bash
# 开发模式
python main.py

# 或者使用uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 访问API文档

启动应用后，访问以下地址查看API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API端点

- `GET /api/v1/` - 根端点
- `GET /api/v1/health` - 健康检查

## 项目结构

```
bsca-expert-agent-api/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   └── agent/
│       ├── __init__.py
│       └── analyzer.py
├── config.py
├── main.py
├── requirements.txt
└── README.md
```

## 开发

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black .
```

## 许可证

MIT License 