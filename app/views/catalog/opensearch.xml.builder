xml.instruct! :xml, :version=>'1.0'
xml.OpenSearchDescription(:xmlns=>'http://a9.com/-/spec/opensearch/1.1/') {
  xml.ShortName application_name
  xml.Description "#{application_name} Search"
  xml.Image "#{asset_url('favicon.ico')}", :height=>16, :width=>16, :type=>'image/x-icon'
  xml.Contact
  xml.Url :type=>'text/html', :method=>'get', :template=>"#{url_for :controller=>'catalog', :only_path => false}?q={searchTerms}"
  xml.Url :type=>'application/rss+xml', :method=>'get', :template=>"#{url_for :controller=>'catalog', :only_path => false}.rss?q={searchTerms}"
  xml.Url :type=>'application/x-suggestions+json', :method=>'get', :template=>"#{url_for :controller=>'catalog',:action => 'opensearch', :format=> 'json', :only_path => false}?q={searchTerms}"
}
