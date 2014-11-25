namespace :cache do
  desc "Remove all saved cache"
  task :expire => :environment do
  	# cache = ActionController::Base.new
  	# cache.expire_fragment("intro_text")
  	# cache.expire_fragment("index_tables")
  	# cache.expire_fragment("popular_papers")
  	# cache.expire_fragment("popular_authors")
  	FileUtils.rm_rf("tmp/cache")
  	FileUtils.rm_rf("public/cache")
  end
end