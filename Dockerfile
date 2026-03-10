# 最小化 Docker 镜像 - 使用国内镜像源
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 使用国内 PyPI 镜像
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制项目代码
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app
ENV DB_HOST=mysql
ENV DB_PORT=3306
ENV DB_USER=quant_user
ENV DB_PASSWORD=quant_pass
ENV DB_NAME=quant_data

# 默认命令
CMD ["python", "test_mock.py"]
