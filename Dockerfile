FROM archlinux
RUN pacman -Syu --noconfirm
RUN pacman -Sy  --noconfirm base-devel git zip unzip wget binutils gcc make asp
RUN pacman -Sy --noconfirm git python3
RUN git clone https://github.com/Semmle/ql
WORKDIR "ql"
RUN wget -q https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql.zip
RUN unzip codeql.zip
WORKDIR ".."
RUN groupadd -r builduser && useradd -m -r -g builduser builduser
WORKDIR "/home/builduser"
USER builduser
RUN asp list-all | shuf | head -n 5 | xargs -d "\n" -n 1 asp checkout
RUN ls
COPY modify_pkgbuilds.sh /home/builduser/
COPY modify_pkgbuild.py /home/builduser/
RUN sh ./modify_pkgbuilds.sh
