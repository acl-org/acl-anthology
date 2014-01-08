module BlacklightHelper
  include Blacklight::BlacklightHelperBehavior

  def application_name
    "ACL anthropoplogy"
  end

  def author_helper_method args
  	args[:document][:author].map!.with_index { |author,i|
  		link_to(author, "/people/" + args[:document][:author_id][i])
  	}
  end

  def volume_helper_method args
  	link_to(args[:document][:volume_anthology], "/volumes/" + args[:document][:volume_id])
  end

  def sig_helper_method args
  	args[:document][:sig_iden].map!.with_index { |sig,i|
  		link_to(sig, "/sigs/" + args[:document][:sig_id][i])
  	}
  end

  def venue_helper_method args
  	args[:document][:venue_name].map!.with_index { |venue,i|
  		link_to(venue, "/venues/" + args[:document][:venue_id][i])
  	}
  end

  def link_to_document(doc, opts={:label=>nil, :counter => nil})
  opts[:label] ||= blacklight_config.index.show_link.to_sym
  label = render_document_index_label doc, opts
  if (doc[:paper_anthology][0] == "W" and doc[:paper_anthology][-2..-1] == "00") or doc[:paper_anthology][-3..-1] == "000"
    puts "yolo"
    link_to label + " [VOLUME]", "/volumes/"+ doc[:volume_id]
  else
    link_to label, "/papers/" + doc[:id]
  end
end

end