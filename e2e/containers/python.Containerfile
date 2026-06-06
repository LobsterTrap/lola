ARG BASE=fedora
FROM localhost/lola-e2e-base-${BASE}:latest

USER root
RUN dnf install -y --setopt=install_weak_deps=False \
    python3 python3-pip \
    && dnf clean all

RUN pip install --no-cache-dir \
    click rich pygments pyyaml python-frontmatter inquirerpy packaging \
    behave uv

USER tester
ENV PATH="/home/tester/.local/bin:${PATH}"
WORKDIR /home/tester/lola

ENTRYPOINT ["e2e/containers/scripts/run-tests.sh"]
