namespace :export do
	desc "Export all bibliography formats one by one for papers."
	task :all_papers => :environment do |t|
		Rake::Task['export:paper_modsxml'].invoke
		Rake::Task['export:paper_bib'].invoke
		Rake::Task['export:paper_ris'].invoke
		Rake::Task['export:paper_endf'].invoke
		Rake::Task['export:paper_word'].invoke
	end
end

namespace :export do
	desc "Export all bibliography formats one by one for volumes."
	task :all_volumes => :environment do |t|
		Rake::Task['export:volume_modsxml'].invoke
		Rake::Task['export:volume_bib'].invoke
		Rake::Task['export:volume_ris'].invoke
		Rake::Task['export:volume_endf'].invoke
		Rake::Task['export:volume_word'].invoke
		Rake::Task['export:volume_dblp'].invoke
		Rake::Task['export:acm_full["csv"]'].invoke
	end
end

namespace :export do
	desc "Export all xml formats one by one."
	task :all_xmls => :environment do |t|
		Rake::Task['export:xml'].invoke
		Rake::Task['export:xml_single'].invoke
		Rake::Task['export:xml_all'].invoke
	end
end