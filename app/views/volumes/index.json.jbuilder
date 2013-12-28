json.array!(@volumes) do |volume|
  json.extract! volume, :id, :anthology_id, :title, :month, :year, :address, :publisher, :url, :bibtype, :bibkey, :sig_id, :venue_id
  json.url volume_url(volume, format: :json)
end
