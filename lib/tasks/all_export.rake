namespace :export do
	desc "Export all bibliography formats for papers (runs paper_modsxml, bib, ris, endf, word)."
	task :all_papers, [:anthology_id] => :environment do |t,args|
		if args[:anthology_id]
			Rake::Task["export:paper_modsxml"].invoke(args[:anthology_id])
			Rake::Task["export:paper_bib"].invoke(args[:anthology_id])
			Rake::Task["export:paper_ris"].invoke(args[:anthology_id])
			Rake::Task["export:paper_endf"].invoke(args[:anthology_id])
			Rake::Task["export:paper_word"].invoke(args[:anthology_id])
		else
			Rake::Task['export:paper_modsxml'].invoke
			Rake::Task['export:paper_bib'].invoke
			Rake::Task['export:paper_ris'].invoke
			Rake::Task['export:paper_endf'].invoke
			Rake::Task['export:paper_word'].invoke
		end
	end
end

namespace :export do
	desc "Export all bibliography formats one by one for volumes (runs volume_modsxml, bib, ris, endf, word, acm_full)."
	task :all_volumes, [:anthology_id] => :environment do |t,args|
		if args[:anthology_id]
			Rake::Task["export:volume_modsxml"].invoke(args[:anthology_id])
			Rake::Task["export:volume_bib"].invoke(args[:anthology_id])
			Rake::Task["export:volume_ris"].invoke(args[:anthology_id])
			Rake::Task["export:volume_endf"].invoke(args[:anthology_id])
			Rake::Task["export:volume_word"].invoke(args[:anthology_id])
			Rake::Task["export:volume_dblp"].invoke(args[:anthology_id])
			Rake::Task["export:acm_volume_csv"].invoke(args[:anthology_id])
		else
			Rake::Task['export:volume_modsxml'].invoke
			Rake::Task['export:volume_bib'].invoke
			Rake::Task['export:volume_ris'].invoke
			Rake::Task['export:volume_endf'].invoke
			Rake::Task['export:volume_word'].invoke
			Rake::Task['export:volume_dblp'].invoke
			Rake::Task['export:acm_full"]'].invoke(args["csv"])
		end
	end
end

namespace :export do
	desc "Export all xml formats (runs xml, xml_single, xml_all)."
	task :all_xmls => :environment do |t|
		Rake::Task['export:xml'].invoke
		Rake::Task['export:xml_single'].invoke
		Rake::Task['export:xml_all'].invoke
	end
end