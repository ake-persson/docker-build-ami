FROM ubuntu:16.04

MAINTAINER Jamie Cho version: 0.16

# Setup sources
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
  bison \
  build-essential \
  curl \
  default-jdk \
  dos2unix \
  ffmpeg \
  flex \
  fuse \
  g++ \
  git \
  libfuse-dev \
  libmagickwand-dev \
  mame-tools \
  markdown \
  python \
  python-dev \
  python-pip \
  python-setuptools \
  ruby \
  software-properties-common \
  vim

# Install useful Python tools
RUN pip install \
  numpy==1.16.5 \
  Pillow==6.2.0 \
  pypng==0.0.20 \
  wand==0.5.7

# Install CoCo Specific stuff
RUN add-apt-repository ppa:tormodvolden/m6809 && \
  echo deb http://ppa.launchpad.net/tormodvolden/m6809/ubuntu trusty main >> /etc/apt/sources.list.d/tormodvolden-m6809-trusty.list && \
  echo deb http://ppa.launchpad.net/tormodvolden/m6809/ubuntu precise main >> /etc/apt/sources.list.d/tormodvolden-m6809-trusty.list && \
  apt-get update && apt-get upgrade -y && apt-get install -y \
  cmoc=0.1.60-0~tormod \
  gcc6809=4.6.4-0~lw9a~trusty \
  lwtools=4.17-0~tormod~~trusty \
  toolshed=2.2-0~tormod

# Install CoCo image conversion scripts
RUN git config --global core.autocrlf input && \
  git clone https://github.com/jamieleecho/coco-tools.git && \
  (cd coco-tools && python setup.py install)

# Install milliluk-tools
RUN git config --global core.autocrlf input && \
  git clone https://github.com/milliluk/milliluk-tools.git && \
  (cd milliluk-tools && git checkout 454e7247c892f7153136b9e5e6b12aeeecc9dd36 && \
  dos2unix < cgp220/cgp220.py > /usr/local/bin/cgp220.py && \
  chmod a+x /usr/local/bin/cgp220.py)

# Install tlidner/cmoc_os9
RUN git clone https://github.com/tlindner/cmoc_os9.git && \
  (cd cmoc_os9/lib && \
  git checkout 9f9dfda1406d152f137131f0670c94d105b9b072 && \
  make && \
  cd ../cgfx && \
  make && \
  cd .. && \
  mkdir -p /usr/share/cmoc/lib/os9 && \
  mkdir -p /usr/share/cmoc/include/os9/cgfx && \
  cp lib/libc.a cgfx/libcgfx.a /usr/share/cmoc/lib/os9 && \
  cp -R include/* /usr/share/cmoc/include/os9 && \
  cp -R cgfx/include/* /usr/share/cmoc/include/os9)

# Install java grinder
RUN git clone https://github.com/mikeakohn/naken_asm.git && \
  git clone https://github.com/mikeakohn/java_grinder && \
  (cd naken_asm && \
  git checkout e9ad7c8181c39ed09bde0d9fd1c285a2ee97edd7 && \
  ./configure && make && make install && \
  cd ../java_grinder && \
  git checkout b3ef7b33343fd877573af5f63502393ffe31f9ab && \
  make && make java && \
  (cd samples/trs80_coco && make grind) && \
  cp java_grinder /usr/local/bin/)

# Clean up
RUN apt-get clean && \
  ln -s /home /Users

# For java_grinder
ENV CLASSPATH=/root/java_grinder/build/JavaGrinder.jar
