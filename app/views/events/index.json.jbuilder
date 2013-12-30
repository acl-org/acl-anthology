json.array!(@events) do |event|
  json.extract! event, :id, :year, :venue_id, :kind
  json.url event_url(event, format: :json)
end
