# Dockerfile for building Overleaf with TeX Live Full (IEEE Standard)
FROM sharelatex/sharelatex:5.0.4

# Install TeX Live Full (IEEE Standard)
RUN tlmgr option repository https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2023/tlnet-final \
    && tlmgr install scheme-full \
    && tlmgr path add

