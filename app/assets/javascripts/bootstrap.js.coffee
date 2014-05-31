jQuery ->
  $("a[rel~=popover], .has-popover").popover()
  $("a[rel~=tooltip], .has-tooltip").tooltip()
  $("#sort-dropdown").attr "title", "Relevance: Sorts based on Best Match and by Year\nYear: Sorts by Year and by ACL venue"
