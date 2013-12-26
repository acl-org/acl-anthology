json.array!(@sigs) do |sig|
  json.extract! sig, :id, :name, :sigid, :url
  json.url sig_url(sig, format: :json)
end
