json.array!(@venues) do |venue|
  json.extract! venue, :id, :acronym, :name, :venueid
  json.url venue_url(venue, format: :json)
end
