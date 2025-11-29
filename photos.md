---
layout: page-no-heading
title: Photos
permalink: /photos/
---

<div class="blog-list">
  <h1 class="page-heading">Photos</h1>

  {% assign has_photos = false %}
  {% assign photo_posts = "" | split: "" %}
  {% for post in site.posts %}
    {% if post.layout == 'photo-page' %}
      {% assign photo_posts = photo_posts | push: post %}
    {% endif %}
  {% endfor %}
  
  {% assign sorted_photos = photo_posts | sort: "title" %}
  
  <div class="post-list">
    {% for post in sorted_photos %}
      {% assign has_photos = true %}
      <article class="post-item">
        {% if post.photo %}
        <div class="photo-thumbnail">
          <a href="{{ post.url | relative_url }}">
            <img src="https://assets.jessefitz.me/cdn-cgi/image/width=200,height=200,fit=cover/images/{{ post.photo }}" alt="{{ post.title | escape }}" />
          </a>
        </div>
        {% endif %}
        <h2 class="post-title">
          <a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a>
        </h2>
        {% if post.excerpt %}
          <p class="post-excerpt">{{ post.excerpt | strip_html | truncatewords: 50 }}</p>
        {% endif %}
      </article>
    {% endfor %}
  </div>
  
  {% unless has_photos %}
    <p class="coming-soon">Coming Soon...</p>
  {% endunless %}
</div>
