FROM archlinux
RUN pacman -Syu --noconfirm
RUN pacman -Sy  --noconfirm base-devel git zip unzip wget binutils gcc make asp
RUN pacman -Sy --noconfirm git python3
RUN groupadd -r builduser && useradd -m -r -g builduser builduser
USER builduser
WORKDIR "/home/builduser"
RUN git clone https://github.com/Semmle/ql
WORKDIR "ql"
RUN wget -q https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql.zip
RUN unzip codeql.zip
WORKDIR ".."
