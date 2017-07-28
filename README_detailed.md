# ACL Anthology - Detailed instructions #

These are the detailed instructions on running the ACL Anthology Rails application which currently drives http://aclanthology.info

These instructions were tested on Debian Wheezy. Througout this document, we'll always assume that your local username is `acl_user`, and that your home directory is `/home/acl_user`.

## Before we start ##

Your first step will be adding some environment variables. This will save typing in the future and prevent some common mistakes.

Open the file `/home/acl_user/.profile` with your favorite editor (if you don't have one, `nano` is a good starting point), and add the following line at the end:

```
export RAILS_ENV=production
```

This variable will be set every time you log in. At this point, you can either log out and log in again for the change to take effect, or you can run the command `source /home/acl_user/.profile`.

You can test your new variable by typing the following command:

```
echo $RAILS_ENV
```

and making sure it prints `production`.

## Installing RVM ##

Follow the instructions in https://rvm.io/rvm/install. As of today (May 2017), those instructions read:

```
gpg --keyserver hkp://keys.gnupg.net --recv-keys 409B6B1796C275462A1703113804BB82D39DC0E3
\curl -sSL https://get.rvm.io | bash -s stable --ruby
```

Note that the second step requires curl. If you don't have it on your system, install it (in Debian) with the command:

```
apt-get install curl
```

You need to have root access to run `apt-get`. The recommended way is through the `sudo` command, like so:

```
sudo apt-get install curl
```

If `sudo` is not properly installed and/or configured in your system, you can use the `su` command instead, like so:

```
# The following command will ask for the root password
su
apt-get install curl
# The following command will take you back to your regular user
exit
```

Once you are done, you want to reload your environment variables, either by logging out and in again, or by writing the following command in all open terminals

```
/home/acl_user/.rvm/scripts/rvm
```

## Installing dependencies ##

For the current installation, you'll need 

  * Rails (4.0.1)
  * Ruby (2.0.0)
  * Bundle (1.3.5)
  * PostgreSQL (9.3.1 or higher)
  * Java (1.5 or higher)

The Anthology is *extremely* dependent on the proper version of each item, so this section will walk you through each step.

### Ruby ###

Ruby can be installed with the following commands.

```
rvm install 2.0.0-p353
```

Then, we add the following line to our /home/acl_user/.profile file in our home directory:

```
rvm use ruby-2.0.0-p353 --default
```

### Rails and Bundle ###

Rails and Bundle can be installed with the following commands:

```
gem install rails -v 4.0.1
gem install bundler -v 1.3.5
```

### PostgreSQL ###

PostgreSQL can be installed with the following command:

```
sudo apt-get install postgresql
```

In our current version of Debian (May 2017) this command installs version 9.1 of PostgreSQL. Knowing that, we install the following dependency:

```
sudo apt-get install postgresql-server-dev-9.1
```

This will install the latest version of PostgreSQL available in your version of Debian, which probably won't be exactly 9.3.1. Luckily for us, this has not caused any problems with our install.

By default, Debian creates neither a user nor a database when installing PostgreSQL. Therefore, we are going to do that now.  First, we'll create the user `pg_acl_user`, with permissions to write to databases, and a database named `db_acl`.

```
sudo su
su postgres
# The following command will ask for a password
createuser -d -P -R -S pg_acl_user
createdb -O pg_acl_user db_acl
exit
exit
```

Then, we need to grant the user access to the database. We have to edit as superusers the file `/etc/postgresql/9.1/main/pg_hba.conf` (for instance, using `sudo nano ...`), and add the following line right below `# TYPE  DATABASE ...`

```
# TYPE  DATABASE  USER  ADDRESS  METHOD
local   all  pg_acl_user     md5
```

Finally, pick up the new configuration by restarting the database server with the following command:

```
sudo /etc/init.d/postgresql restart
```

### Java ###

While Debian provides a Java implementation, we want to use the official one.

Following the instructions laid out in [this website](https://www.digitalocean.com/community/tutorials/how-to-manually-install-oracle-java-on-a-debian-or-ubuntu-vps), first you need to download Java from the official Oracle website. In our case, the file is called `jdk-8u131-linux-x64.tar.gz`.

Once you have your file, these are the required commands:

```
sudo su
mkdir /opt/jdk
tar -zxvf jdk-8u131-linux-x64.tar.gz -C /opt/jdk/
update-alternatives --install /usr/bin/java java /opt/jdk/jdk1.8.0_131/bin/java 100
update-alternatives --install /usr/bin/javac javac /opt/jdk/jdk1.8.0_131/bin/javac 100
exit
```

## Cloning the source code ##

To clone the source code for the Anthology, you need these commands

```
sudo apt-get install git
git clone https://github.com/WING-NUS/acl
```

Once the cloning is done, go to the ACL directory and install all gems

```
cd acl
bundle install
```

Then, edit the file `acl/config/database.yml` and, under "production" (end of the file), change username and password to the user `pg_acl_user` and the password you chose when setting up the user. Once that's done, you can create the database with the following commands:

```
rake db:create
rake db:migrate
```

## Seeding the database ##

You can now seed the database. This will take a long time, so be prepared.

In theory, it should be enough with a single command:

```
rake db:seed
```

If your system has some policy controls regarding use of memory and/or CPU, this command will fail. If that's your case, you can seed individual elements.

The following script will seed all elements, one at the time:

```
cd acl/import
for file in *xml; do name=`basename -s .xml $file`; rake import:xml[true,$name]; done > debug.log
```

This method is considerably slower (it took more than a full day in our previous VM, and around 3hs in the current one), but if there's an error with a specific file it will just store the error message in `debug.log` and move on to the next one.

The other import commands work without any issues:

```
rake import:sigs[true]
rake import:venues[true]
rake import:events[true]
```

## Indexing ##
First, we edit the file `acl-anthology/jetty/solr/blacklight-core/conf/data-config.xml` to enter the proper username and password for the PotsgreSQL database. In line 5, write:

```
user=pg_acl_user
password=<the password you created above after installing PostgreSQL>
```

Then, edit line 67 of `acl_anthology/jetty/solr/blacklight-core/conf/solrconfig.xml` and change

```
<str name="config">/var/opt/solr/solr/blacklight-core/conf/data-config.xml</str>
```

to

```
<str name="config">data-config.xml</str>
```

And finally, change line 80 of `acl_anthology/jetty/etc/jetty.xml` to `127.0.0.1`.

At this point, we can start running jetty with the following commands:

```
cd acl/jetty
java -jar start.jar &
rake acl:reindex_solr
```

TIP: you might want to use [GNU Screen](https://www.linux.com/learn/taking-command-terminal-gnu-screen) to keep the task running in the background. You can use the following commands instead:

```
sudo aptitude install screen
cd acl/jetty
# The following command will start a new console
screen
java -jar start.jar
# Press and hold the Ctrl key, and type 'ad' to go back to your previous console
rake acl:reindex_solr
```

Please refer to the official GNU Screen documentation for more details.

In either case, the last line will start the indexing process. There's a way to check how is the task going, but this is work in progress. Please get in contact with us for an update on this.

## Exporting ##

We need to export all papers to the proper formats (bib, endf, and so on).

First, we need to install some auxiliary utilities and create a missing directory:

```
sudo install bibutils
mkdir acl/export/endf
```

We are now ready to export. There's a command to do this all at once, namely

```
rake export:all papers
```

The problem, however, is that this task takes too long and it can be killed by the OS. You can find a way to fix that, or if that fails, you can run the following script. The script will be slower, but it will start and stop for each paper, so it won't run out of resources.

```
cd acl
for file in import/*xml
do
      volume=`grep '<volume id' $file | sed 's/.*volume id=.\(.*\).>.*/\1/'`
      for paper in `grep "paper id" $file | sed 's/.*id=.\([0-9]\+\).*/\1/'`
      do
              rake export:all_papers[${volume}-${paper}]
      done
done
```
