# Be sure to restart your server when you modify this file.Mime::Type.register_alias "text/plain", :refworks_marc_txt
Mime::Type.register_alias "text/plain", :openurl_kev
Mime::Type.register "application/x-endnote-refer", :endnote
Mime::Type.register "application/marc", :marc
Mime::Type.register "application/marcxml+xml", :marcxml, 
      ["application/x-marc+xml", "application/x-marcxml+xml", 
       "application/marc+xml"]


# Add new mime types for use in respond_to blocks:
# Mime::Type.register "text/richtext", :rtf
# Mime::Type.register_alias "text/html", :iphone
