json.array!(@papers) do |paper|
  json.extract! paper, :id, :volume_id, :anthology_id, :title, :month, :year, :address, :publisher, :pages, :url, :bibtype, :bibkey, :attachment, :attach_type
  json.url paper_url(paper, format: :json)
end
