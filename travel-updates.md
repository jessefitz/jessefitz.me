---
#layout: page-no-heading
#title: Travel
#permalink: /travel/
---

Here's where I'll share some details about the plan (ideas) for my unplanned trip.  I'll update with additional postings as the trip progresses.

{% assign travel_posts = site.categories.travel | sort: 'date' | reverse %}
{% for post in travel_posts %}
- **[{{ post.title }}]({{ post.url }})**  
  _Posted on: {{ post.date | date: "%B %d, %Y" }}_  
  {{ post.excerpt }}
{% endfor %}
