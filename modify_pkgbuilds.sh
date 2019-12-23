for i in  ./*; do
    if [ -d i ]
    then
        cd /home/builduser/$i/trunk;
        python3 /home/builduser/modify_pkgbuild.py;
        cd /home/builduser;
    fi
done
