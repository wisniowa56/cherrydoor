SUDO=''
if (( $EUID != 0 )); then
    SUDO='sudo';
fi;
while true; do
    read -p "Zainstalować aktualizację, jeśli jest dostępna? (y/n) " update
    case $update in
        y|Y|yes|Yes|tak|Tak ) 
            branch=$(git symbolic-ref --short HEAD);
            git fetch;
            git reset --hard origin/$branch;
            break;;
        n|N|no|No|nie|Nie ) break;;
        * ) continue;;
    esac
done
if [ ! -f "config.json" ]; then
    cp install/config.json config.json
fi;
if hash mongo &>/dev/null; then
    echo -e "\e[92mMongoDB jest zainstalowane\e[39m";
else
    echo -e "\e[93mMongoDB niezainstalowane. Instalowanie...\e[39m"
    $SUDO wget -qO - https://www.mongodb.org/static/pgp/server-4.2.asc | $SUDO apt-key add - &&
    echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.2 multiverse" | $SUDO tee /etc/apt/sources.list.d/mongodb-org-4.2.list &&
    $SUDO apt-get update &&
    $SUDO apt-get install -y mongodb-org;
    $SUDO service mongod start;
fi;
if hash pip3 &>/dev/null; then
    echo -e "\e[92mpip3 jest zainstalowane, instalowanie wymaganych modułów\e[39m";
else
    echo -e "\e[93mpip3 niezainstalowane. Instalowanie...\e[39m" &&
    $SUDO apt-get install python3-pip;
fi;
if ! (locate libffi); then 
    echo -e "\e[93mlibffi niezainstalowane. Instalowanie...\e[39m" &&
    $SUDO apt-get install build-essential libffi-dev &&
    $SUDO apt-get install python3-cffi;
fi;

pip3 install -r requirements.txt

echo -e "--------------------------------------------------------"

while true; do
    read -p "Skonfigurować mongodb? (y/n) " mongoconfig
    case $mongoconfig in
        y|Y|yes|Yes|tak|Tak ) 
            cat <(echo "var config = ") config.json > install/config.js;
            while true; do
                read -p "Skonfigurować konto administratora? (y/n) " admin
                case $admin in
                    y|Y|yes|Yes|tak|Tak ) 
                        read -p "Nazwa użytkownika: " username;
                        read -sp "Haslo: " password;
                        $SUDO apt-get install -y argon2
                        read hashed_password < <(echo -n "$password" | argon2 gktIC5njny5F70t+ -id -m 16 -t 4 -p 8 -e)
                        echo "var user = {\"username\":\"$username\", \"password\":\"$hashed_password\"}" >> install/config.js;
                        break;;
                    n|N|no|No|nie|Nie ) echo 'var user = {}' >> install/config.js; 
                        break;;
                    * ) continue;;
                esac
            done
            mongo install/mongo-config.js;
            rm -rf install/config.js;
            break;;
        n|N|no|No|nie|Nie ) break;;
        * ) continue;;
        
    esac
done