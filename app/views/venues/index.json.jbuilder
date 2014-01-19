json.array!(@venues) do |venue|
  json.extract! venue, :id, :acronym, :name, :venue_type
  json.url venue_url(venue, format: :json)
end
