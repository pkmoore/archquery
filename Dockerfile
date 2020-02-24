FROM archlinux
RUN pacman -Syu --noconfirm
RUN pacman -Sy  --noconfirm base-devel git zip unzip wget binutils gcc make asp
RUN pacman -Sy --noconfirm git python3
RUN groupadd -r builduser && useradd -m -r -g builduser builduser
RUN groupadd sudo
RUN usermod -a -G sudo builduser
RUN echo "builduser ALL=NOPASSWD: ALL" >> /etc/sudoers
RUN mkdir /home/builduser/.archquery
RUN chown -R builduser:builduser /home/builduser/.archquery
USER builduser
WORKDIR "/home/builduser"
RUN git clone https://github.com/Semmle/ql
WORKDIR "ql"
RUN wget -q https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql.zip
RUN unzip codeql.zip
WORKDIR ".."
