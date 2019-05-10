#!/bin/sh

# Downloads Raspbian SD image and prepares it for testing (enable SSH and add trusted key)
# Downloads also the dependencies (kernel and dtb file) for QEMU emulation

set -e

currdir=$(pwd)
scriptdir=$(cd `dirname $0` && pwd)
workdir=$(mktemp -d)

#TODO: Verify image with md5sum
if [ -f 2019-04-08-raspbian-mender-testing.img ]; then
    echo "Found testing image in current directory. Exiting"
    exit 0;
fi

# Get superuser privilages to be able to mount the SD image
sudo true

cd ${workdir}

echo "##### Donwloading and extracting..."
wget https://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-2019-04-09/2019-04-08-raspbian-stretch-lite.zip
unzip 2019-04-08-raspbian-stretch-lite.zip
wget https://raw.githubusercontent.com/dhruvvyas90/qemu-rpi-kernel/master/kernel-qemu-4.14.79-stretch
wget https://raw.githubusercontent.com/dhruvvyas90/qemu-rpi-kernel/master/versatile-pb.dtb

echo "##### Preparing image for tests..."
boot_start=$(fdisk -l 2019-04-08-raspbian-stretch-lite.img | grep Linux | tr -s ' ' | cut -d ' ' -f2)
sector_size=$(fdisk -l 2019-04-08-raspbian-stretch-lite.img | grep '^Sector' | cut -d' ' -f4)
offset=$(expr $boot_start \* $sector_size)
mkdir img-rootfs
sudo mount -o loop,offset=$offset 2019-04-08-raspbian-stretch-lite.img img-rootfs

sudo mkdir img-rootfs/home/pi/.ssh
cat ${scriptdir}/ssh-keys/key.pub | sudo tee img-rootfs/home/pi/.ssh/authorized_keys
sudo ln -s /lib/systemd/system/ssh.service img-rootfs/etc/systemd/system/multi-user.target.wants/ssh.service
sync
sudo umount img-rootfs

mv 2019-04-08-raspbian-stretch-lite.img ${currdir}/2019-04-08-raspbian-mender-testing.img
mv kernel-qemu-4.14.79-stretch ${currdir}/
mv versatile-pb.dtb ${currdir}/

cd ${currdir}
rm -rf ${workdir}

echo "##### Done"

exit 0
