ARG NODE_IMAGE=node:20-bookworm-slim
ARG PYTHON_IMAGE=python:3.11-slim-bookworm
ARG PNPM_VERSION=10.33.1


FROM ${NODE_IMAGE} AS web-builder

ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG PNPM_VERSION

WORKDIR /build/web

COPY web/package.json web/pnpm-lock.yaml ./
RUN npm install -g pnpm@${PNPM_VERSION} --registry=${NPM_REGISTRY} \
    && pnpm config set registry ${NPM_REGISTRY} \
    && pnpm install --frozen-lockfile

COPY web/ ./
RUN pnpm run build


FROM ${PYTHON_IMAGE} AS python-base

ARG APT_MIRROR=https://mirrors.ustc.edu.cn/debian
ARG APT_SECURITY_MIRROR=https://mirrors.ustc.edu.cn/debian-security

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    TZ=Asia/Shanghai \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i "s|http://security.debian.org/debian-security|${APT_SECURITY_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
      sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates tzdata; \
    ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime; \
    echo "${TZ}" > /etc/timezone; \
    rm -rf /var/lib/apt/lists/*


FROM python-base AS python-builder

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /build

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends build-essential gcc libffi-dev python3-dev; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel -i ${PIP_INDEX_URL} \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt -i ${PIP_INDEX_URL}


FROM python-base AS runtime

WORKDIR /opt/vue-fastapi-admin

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends nginx; \
    rm -rf /var/lib/apt/lists/*; \
    rm -f /etc/nginx/sites-enabled/default

COPY --from=python-builder /opt/venv /opt/venv
COPY app ./app
COPY migrations ./migrations
COPY pyproject.toml requirements.txt run.py ./
COPY deploy/web.conf /etc/nginx/sites-available/web.conf
COPY deploy/entrypoint.sh /entrypoint.sh
COPY --from=web-builder /build/web/dist ./web/dist

RUN set -eux; \
    ln -sf /etc/nginx/sites-available/web.conf /etc/nginx/sites-enabled/web.conf; \
    chmod +x /entrypoint.sh; \
    mkdir -p storage/knowledge storage/exam/banks app/logs

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/opt/vue-fastapi-admin

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
