# syntax=docker/dockerfile:1
# check=skip=InvalidDefaultArgInFrom
ARG OVERLEAF_VERSION
# Dockerfile for building Overleaf with TeX Live Full (IEEE Standard)
FROM sharelatex/sharelatex:${OVERLEAF_VERSION}

ARG TEXLIVE_REPO=""
# Install TeX Live Full (IEEE Standard)
RUN set -eu; \
    if [ -n "${TEXLIVE_REPO}" ]; then \
    tlmgr option repository "${TEXLIVE_REPO}"; \
    fi; \
    tlmgr install scheme-full; \
    tlmgr path add