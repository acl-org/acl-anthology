# encoding: utf-8
# -*- ruby-mode -*-

namespace :popular do
  desc "Compile popular authors"
  task :authors => :environment do
    1;
  end
  
  desc "Compile popular papers"
  task :papers => :environment do 
    files = Dir["/tmp/*access_log"]
    cmd = "cat #{files[0]} | grep -vi bot | grep -vi spider"
    freq = Hash.new(1)
    IO.popen(cmd).each_line do |l|
      if (l[/GET \/papers/] != nil && l[/\.bib/] == nil)
        key = l[/GET \/papers[^ ]*/]
        freq[key] = freq[key] + 1 || 1
      end
    end

    puts freq.sort_by {|_key, value| value}.reverse
  end
end
