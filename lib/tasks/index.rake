namespace :acl do
  desc "Remove all solr indexes"
  task :remove_index_solr => :environment do
  	puts `curl http://localhost:8983/solr/blacklight-core/update -H "Content-Type: text/xml" --data-binary '<delete><query>*:*</query></delete>`
  end
end

namespace :acl do
  desc "Index data into Solr"
  task :index_solr => :environment do
  	puts `curl http://localhost:8983/solr/dataimport?command=full-import`
  end
end

namespace :acl do
  desc "Reindex data into Solr"
  task :reindex_solr => :environment do
  	puts `curl http://localhost:8983/solr/blacklight-core/update -H "Content-Type: text/xml" --data-binary '<delete><query>*:*</query></delete>`
  	puts `curl http://localhost:8983/solr/dataimport?command=full-import`
  end
end