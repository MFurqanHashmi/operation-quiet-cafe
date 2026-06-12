FROM debian:bookworm-slim

# Station Bravo: the remote post the team must securely reach (Missions 5 & 6).
# Password auth is OFF. The backend holds a baked "bootstrap" key to provision
# each session's freshly generated key, then logs in with that session key to
# prove key-based auth and read the planted flag.

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/run/sshd

# Operator account the team logs in as.
RUN useradd -m -s /bin/bash bob

# Install the backend's bootstrap public key.
RUN mkdir -p /home/bob/.ssh \
    && echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFqKfjC1dPJV2Jt3vRRWGXfUDbB7M8SlWQHBP1dcUlRj cafe-bootstrap" \
        > /home/bob/.ssh/authorized_keys \
    && chmod 700 /home/bob/.ssh \
    && chmod 600 /home/bob/.ssh/authorized_keys \
    && chown -R bob:bob /home/bob/.ssh

# Plant the Mission 5 flag, readable only after a successful login as bob.
RUN echo "QC{my_secret_never_left_home}" > /home/bob/flag.txt \
    && chown bob:bob /home/bob/flag.txt \
    && chmod 600 /home/bob/flag.txt

# Harden: keys only, no passwords, no root login.
RUN sed -i 's/#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config \
    && sed -i 's/#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]
