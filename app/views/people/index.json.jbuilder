json.array!(@people) do |person|
  json.extract! person, :id, :person_id, :first_name, :last_name, :full_name
  json.url person_url(person, format: :json)
end
