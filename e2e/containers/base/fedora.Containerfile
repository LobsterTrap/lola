FROM registry.fedoraproject.org/fedora:latest

RUN dnf install -y --setopt=install_weak_deps=False \
    git curl ca-certificates \
    && dnf clean all

RUN useradd --create-home --shell /bin/bash tester
USER tester
WORKDIR /home/tester
