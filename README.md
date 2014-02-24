# ACL Anthology#
Basic instructions on running the ACL anthology

## Installation ##
These are the main steps to getting the ACL anthology running on your local machine. The whole process should take at least an hour or so, so be prepared. This is best done on any Linux based OS (MacOS, Ubuntu, Linux...) for the convience of tools used.

### Prerequisites ###
The installation of this rails app assumes that you have a running Ruby on Rails installation with the following versions of core services:
```
  * Rails (4.0.1)
  * Ruby (2.0.0)
  * Bundle (1.3.5)
  * PostgreSQL (9.3.1)
  * Java (1.5 or higher)
```
If you don't have a running copy, we recommend using RVM to install Rails and all its dependencies. Also, git command line tools or GUI is needed to clone the repository.

### Cloning ###
Browse to your designated folder and clone it using this git command (or with a git GUI tool). The process should take a while since the repository is quite big (about 150MB):
```
$ git clone https://github.com/zamakkat/acl
```
After the cloning is done, go to the ACL directory and install all gems:
```
$ cd acl
$ bundle install
```

### Database ###
Run the following commands to initialize the database and run migrations:
```
$ rake db:create
$ rake db:migrate
```
Ingest the database with the ACL anthology information using this command:
```
$ rake db:seed
```
This command requires Internet connectivity as it gets the data directly from the ACL website. To fully ingest the data, it will take a very long time, at least 30 mins. So you can go grab a coffie or a meal or something :) 

If there is any error with the seeding process, most probably there is a problem with some of the xml files. Go to db/seeds.rb, ignore those files for the time being and inform the ACL editor to edit those xml files. In this case, or if for any reason you want to recreate and reseed the database, please use the drop command:
```
$ rake db:drop
```
After that you can start over with recreating the database.

### Indexing ###
Before using the search functionality, we will need to run the Solr server locally and index the data. First, we will need to set the user. Open `jetty/solr/blacklight-core/conf/data-config.xml` (or just use find to find this file) and change line 5 to your current user account:
```
user="user_account"
```
After saving the file, we can start the Solr server:
```
$ cd jetty; java -jar start.jar &
```
Open a new terminal window and index the data:
```
$ rake acl:reindex_solr 
```
At this point, your setup is completed and you can run the rails server to test the app:
```
$ rails server
```
You can go to the ACL rails app by going to http://localhost:3000/ in you browser.

As of writing, the first page you will see is the Blacklight search page. Other pages you can browse through include:
```
http://localhost:3000/volumes
http://localhost:3000/people
http://localhost:3000/sigs
http://localhost:3000/venues
```

## Exporting data ##

### Bib and DBLP Export ###

For the export function to work properly, we must first run some rake tasks to generate the exported files. The code can be found in `lib/tasks/bib_export.rake`(As of writing, there MAY be some files that cannot be exported due to some problems with Bibutils). To start the export, this 2 commands should be run first as the other exports rely on them:
```
$ rake export:export_paper_modsxml
$ rake export:export_volume_modsxml
```
After that, we can run all of the foloowing commands in any order you prefer:
```
$ rake export:export_paper_bib
$ rake export:export_paper_ris
$ rake export:export_paper_endf
$ rake export:export_paper_word
$ rake export:export_paper_dblp
$ rake export:export_volume_bib
$ rake export:export_volume_ris
$ rake export:export_volume_endf
$ rake export:export_volume_word
$ rake export:export_volume_dblp
```

### ACM Export ###
For the ACM format, we have a different task in `lib/tasks/acm_export.rake`. The ACM format consist of a zip of the pdf papers and a csv file of all the papers in that volume. There are a few different tasks that could be run:

To export only the zip or csv file for E13-1:
```
$ rake export:acm_volume_zip["E13-1"]
$ rake export:acm_volume_csv["E13-1"]
```
To export zip or csv files for all volumes in the anthology:
```
$ rake export:acm_full["zip"]
$ rake export:acm_full["csv"]
```
To export everything in one line:
```
$ rake export:acm_full
```

### XML Export ###

We allow to export all information in the ACL database to xml files in different formats. To export the data:
```
$ rake export:xml
$ rake export:xml_single
$ rake export:xml_all
```
The saved data will be exported to a the folder export.
The first command exports the anthology in the standard xml file: E12.xml
The second one exports each individual volume in a single xml file: E12-1.xml
The third command exports the full anthology into a single xml file: acl_anthology.xml

## License ##
ACL materials are Copyright (C) 1963-2013 ACL; other materials are copyrighted by their respective copyright holders. All materials here are licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 License . Permission is granted to make copies for the purposes of teaching and research.

Credits: The institutions and individuals behind the ACL Anthology.

Min-Yen Kan (Editor, 2008-) / Steven Bird (Editor, 2001-2007) 
