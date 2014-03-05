namespace :acl do
  desc "Create default roles"
  task :roles => :environment do
  	['user', 'moderator', 'admin'].each do |role|
	  Role.find_or_create_by_name role
	end
  end
end