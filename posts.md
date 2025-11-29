---
layout: page-no-heading
title: Posts
permalink: /posts/
---

<div class="blog-list">
  <h1 class="page-heading">Posts</h1>

  {% assign has_posts = false %}
  <div class="post-list">
    {% for post in site.posts %}
      {% unless post.path contains 'archive' or post.layout == 'photo-page' %}
        {% assign has_posts = true %}
        <article class="post-item">
          <h2 class="post-title">
            <a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a>
            <span class="post-date">({{ post.date | date: "%b %-d, %Y" }})</span>
          </h2>
          {% if post.excerpt %}
            <p class="post-excerpt">{{ post.excerpt | strip_html | truncatewords: 50 }}</p>
          {% endif %}
        </article>
      {% endunless %}
    {% endfor %}
  </div>
  
  {% unless has_posts %}
    <p class="coming-soon">Coming Soon...</p>
  {% endunless %}
</div>


