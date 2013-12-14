json.array!(@papers) do |paper|
  json.extract! paper, :id, :volume_id, :paper_id, :title, :month, :year, :address, :publisher, :pages, :url, :bibtype, :bibkey
  json.url paper_url(paper, format: :json)
end
