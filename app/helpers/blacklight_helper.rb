module BlacklightHelper
  include Blacklight::BlacklightHelperBehavior

  def application_name
    "ACL Anthology"
  end

  def author_helper_method args
  	args[:document][:author].map! { |author|
  		link_to(author, person_path(Person.where(full_name: author).first))
  	}
  end

  def volume_helper_method args
    vol_id = args[:document][:volume_anthology]
  	link_to(vol_id, volume_path(Volume.where(anthology_id: vol_id).first))
  end

  def sig_helper_method args
  	# args[:document][:sig_iden].map! { |sig|
  	# 	link_to(sig, sig_path(Sig.find(sig)))
  	# }
  end

  def venue_helper_method args
  	# args[:document][:venue_name].map! { |venue|
  	# 	link_to(venue, venue_path(Venue.find(venue)))
  	# }
  end

  def link_to_document(doc, opts={:label=>nil, :counter => nil})
  opts[:label] ||= blacklight_config.index.show_link.to_sym
  label = render_document_index_label doc, opts
  if (doc[:paper_anthology][0] == "W" and doc[:paper_anthology][-2..-1] == "00") or doc[:paper_anthology][-3..-1] == "000"
    link_to label + " [VOLUME]", volume_path(Volume.find(doc[:volume_id]))
  else
    link_to label, paper_path(Paper.find(doc[:id]))
  end
end

end