---
 layout: page-no-heading
 title: Blog
 permalink: /Blog/
---
# The Reset
On **Day 0 - *n*** I decided it was time to reset.  

A reset brings new perspectives, ideas and opportunities.  It's a time to explore.  It's a time to experiment.

A reset is a great opportunity to establish new routines.

Following is new routine I'm establishing during this reset.

### Phase 1
{% assign phase0_posts = site.categories.Phase0 | default: site.categories["Phase0"] %}

{% assign sorted_phase0_posts = phase0_posts | sort: "date" %}

{% if sorted_phase0_posts.size > 0 %}
  {% for post in sorted_phase0_posts %}
 - [{{ post.title }}]({{ post.url }}) - {{ post.tagline }}
  {% endfor %}
{% else %}
  <p>No posts found in this category.</p>
{% endif %}

