---
title: Creating OG Images for Static Pages with Rust
slug: og-image-generator
date: 2024-11-30
taxonomies:
  tags: ["rust", "svg", "ogp"]
---

OGP ([Open Graph Protocol](https://ogp.me/)) is an HTML meta-tags specification for websites to make links look nice in third-party services such as Facebook, X, LinkedIn or chat apps. OGP also allows to specify a link to page thumbnail that will be shown as preview when link shared, which can increase clickability.

Some blog engines have built-in functions for this. I use [Zola](https://getzola.org/) (static page generator) to create pages for this blog. Unfortunately, Zola does not have an ability to generate OG images. This can be achieved with external tools or scripts during the build process. Another approach to use edge functions (such as [vercel/og](https://vercel.com/docs/functions/og-image-generation)) to generate thumbnails on the fly. However, this approach relies on a specific service provider, which I want to avoid.

I thought, why not use OG image generation as a service? I searched around and found [og-image-generator](https://github.com/sagarhani/og-image-generator) by sagarhani.

The functionality of `og-image-generator` worked well for me, and I used it for this blog for some time. However, the project seems abandoned, and I'm unsure how the author feels about additional load on their service. I decided it shouldn't be too hard to create a similar service myself — a single endpoint for generating images with search params. Moreover, when I looked into the source code of `og-image-generator`, I noticed that it launches Chrome to render an image from HTML, which felt like significant overhead to me.

## Coding

I need an endpoint that accepts: article title, URL/domain, author name and avatar via search parameters. Lately, I've been using Rust for most of my pet projects, so I decided to build this service with Rust as well. I added a route in `axum` and implemented a handler that generates SVG images, using some basic math to calculate the positioning of elements. The size of the OG image is predefined as `1200x630`, following the specefication. SVG allows the use of a `<style>` tag, making it easy to customise default font-family.

The only challenge I encountered was creating a mask for the image. I initially thought SVG might have some syntactic sugar for this, but it essentially works the same way as masks in Photoshop.

Example of SVG generation ([`maud`](https://maud.lambda.xyz/) is an HTML template engine on Rust macros):

```rust
use maud::{html, Markup};

fn render_svg(title: &str, author: &str, url: &str, photo: &str) -> Markup {
  let (w, h) = (1200, 630);

  let pic_r = 50;
  let pic_y = h - 128;
  let l1y = pic_y - (pic_r - 10) / 2 + 48 / 2 - 6;
  let l2y = pic_y - (pic_r - 10) / 2 + 32 / 2 + 6 + 32;

  html!(svg xmlns="http://www.w3.org/2000/svg" viewBox=(format!("0 0 {} {}", w, h)) width=(w) height=(h) {
    style { ("text { font-family: 'Open Sans', Arial, sans-serif; }" ) }

    rect x="0" y="0" width=(w) height=(h) fill="black" stroke="white" stroke-width="16" {}
    text x=(120) y=(200) font-weight="700" font-size="72" fill="white" { (title) }
    text x=(200) y=(l1y) font-weight="700" font-size="48" fill="white" { (author) }
    text x=(200) y=(l2y) font-weight="400" font-size="32" fill="white" { (url) }
    (circle_avatar(photo, 128, pic_y, pic_r))
  })
}

fn circle_avatar(url: &str, cx: u32, cy: u32, radius: u32) -> Markup {
  html!({
    defs {
      clipPath id="circle-photo" { circle cx=(cx) cy=(cy) r=(radius) {} }
    }

    g clip-path="url(#circle-photo)" {
      image href=(url) x=(cx-radius) y=(cy-radius) width=(radius * 2) height=(radius * 2) {}
      circle cx=(cx) cy=(cy) r=(radius) stroke="white" stroke-width="4" fill="none" {}
    }
  })
}
```

And then the SVG image is generated in the Axum handler:

```rust
use axum::extract::{Query, Request};
use axum::http::{header, StatusCode};
use axum::response::IntoResponse;
use std::collections::HashMap;

async fn svg_handler(req: Request) -> Res<impl IntoResponse> {
  let qs: Query<HashMap<String, String>> = Query::try_from_uri(req.uri())?;
  let title = qs.get("title").cloned().unwrap_or("This is default article title".to_string());
  let author = qs.get("author").cloned().unwrap_or("Author".to_string());
  let url = qs.get("url").cloned().unwrap_or("https://example.com".to_string());
  let photo = qs.get("photo").cloned().unwrap_or("https://gravatar.com/avatar/".to_string());

  let svg = render_svg(&title, &author, &url, &photo);
  Ok((StatusCode::OK, [(header::CONTENT_TYPE, "image/svg+xml")], svg))
}
```

This code will generate the following SVG:

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630"><style>text { font-family: 'Open Sans', Arial, sans-serif; }</style><rect x="0" y="0" width="1200" height="630" fill="black" stroke="white" stroke-width="16"></rect><text x="120" y="200" font-weight="700" font-size="72" fill="white">This is default article title</text><text x="200" y="500" font-weight="700" font-size="48" fill="white">Author</text><text x="200" y="536" font-weight="400" font-size="32" fill="white">https://example.com</text><defs><clipPath id="circle-photo"><circle cx="128" cy="502" r="50"></circle></clipPath></defs><g clip-path="url(#circle-photo)"><image href="https://gravatar.com/avatar/" x="78" y="452" width="100" height="100"></image><circle cx="128" cy="502" r="50" stroke="white" stroke-width="4" fill="none"></circle></g></svg>

The endpoint can accept `title`, `author`, `url` and `photo` in the search params, and these values will be passed to SVG template. That's pretty much it, I thought, deployed the service to [fly.io](/deploy-fastapi-with-sqlite-on-flyio/), updated the blog links, went to check how new preview looked, and the thumbnail didn't display.

It turned out that OG images cannot be SVG (which makes sense, because then different mobile clients would need to be able to render it, which is harder then showing prepared image).

## SVG to PNG

It's not a big deal, I thought. A lot things has already been rewritten in Rust, and there's probably a ready to use solution for SVG rendering, especially since I found several popular crates for this. But it turned out to be more complicated than expected. Rendering SVG to PNG is quite a complex task, and the SVG specification is huge, so libs not fully implement the specification. However, I only need basic SVG support. I tried several crates and settled on `resvg`. I wrote a rendering function:

```rust
use resvg::{tiny_skia, usvg};

fn render_png(svg: &str) -> Vec<u8> {
  let tree = {
    let mut opt = usvg::Options::default();
    opt.fontdb_mut().load_system_fonts();
    usvg::Tree::from_str(svg, &opt).unwrap()
  };

  let size = tree.size().to_int_size();
  let mut pixmap = tiny_skia::Pixmap::new(size.width(), size.height()).unwrap();
  resvg::render(&tree, tiny_skia::Transform::default(), &mut pixmap.as_mut());
  pixmap.encode_png().unwrap()
}
```

And updated handlers:

```rust
// in some reason axum not allow to pass Request as ref – code will not compile, so req.uri() used
async fn prepare_svg(uri: &axum::http::Uri) -> Res<String> {
  let qs: Query<HashMap<String, String>> = Query::try_from_uri(uri)?;
  let title = qs.get("title").cloned().unwrap_or("This is default article title".to_string());
  let author = qs.get("author").cloned().unwrap_or("Author".to_string());
  let url = qs.get("url").cloned().unwrap_or("https://example.com".to_string());
  let photo = qs.get("photo").cloned().unwrap_or("https://gravatar.com/avatar/".to_string());
  Ok(render_svg(&title, &author, &url, &photo).into_string())
}

async fn svg_handler(req: Request) -> Res<impl IntoResponse> {
  let svg = prepare_svg(req.uri()).await?;
  Ok((StatusCode::OK, [(header::CONTENT_TYPE, "image/svg+xml")], svg))
}

async fn png_handler(req: Request) -> Res<impl IntoResponse> {
  let svg = prepare_svg(req.uri()).await?;
  let png = render_png(&svg);
  Ok((StatusCode::OK, [(header::CONTENT_TYPE, "image/png")], png))
}
```

I run it, and generally, everything works, but the avatar doesn't show up.

<img src="/ogi-image-generator-1.png" />

## Loading remote images

`resvg` itself cannot load images from remote URLs used in SVG, but it can render images from a base64-encoded data string. Okay, I'll load the image and convert it myself:

```rust
use base64::Engine;
use reqwest::header::{HeaderMap, HeaderValue};

async fn load_base64_image(url: &str) -> Res<String> {
  let ua = format!("{}/{}", env!("CARGO_PKG_NAME"), env!("CARGO_PKG_VERSION"));

  let mut headers = HeaderMap::new();
  headers.insert("User-Agent", HeaderValue::from_str(&ua)?);

  let client = reqwest::Client::builder()
    .default_headers(headers)
    .read_timeout(std::time::Duration::from_secs(10))
    .build()?;

  let rep = client.get(url).send().await?;

  let max_size = 1024 * 1024 * 5; // 5MB
  match rep.content_length() {
    None => return AppError::new("Image size is unknown"),
    Some(len) if len > max_size => return AppError::new("Image is too large"),
    _ => {}
  };

  let allowed = ["image/jpeg", "image/png", "image/webp", "image/svg+xml"];
  let mime = match rep.headers().get(header::CONTENT_TYPE) {
    None => return AppError::new("Content type is unknown"),
    Some(ct) if !allowed.contains(&ct.to_str().unwrap()) => {
      return AppError::new(&format!("Content type is not allowed: {:?}", ct))
    }
    Some(ct) => ct.to_str().unwrap().to_string(),
  };

  let rep = rep.bytes().await?;
  let rep = base64::engine::general_purpose::STANDARD.encode(rep);
  Ok(format!("data:{mime};base64,{rep}"))
}

async fn prepare_svg(uri: &axum::http::Uri) -> Res<String> {
  // ...
  let photo = qs.get("photo").cloned().unwrap_or("https://gravatar.com/avatar/".to_string());
  let photo = load_base64_image(&photo).await?;
  Ok(render_svg(&title, &author, &url, &photo).into_string())
}
```

I check generation again – everything is fine, the avatar is present in the final render:

<img src="/ogi-image-generator-2.png" />

## Docker image

So, the service is ready. Now, just needed to pack code into a [Docker image](/fast-multi-arch-docker-for-rust). It's pretty much the same as usual, except that fonts files should be added to image too. I usually use Alpine images, and fonts can be added via `apk`:

```Dockerfile
FROM alpine:latest
RUN apk add --no-cache ttf-opensans
WORKDIR /app
# ... copy and run bin file
```

## Fin

I added a template and copied themes from `sagarhani/og-image-generator`. I also created a preview page where you can experiment with the generation. This is enough for my current needs, but if anyone needs more, Issues/PRs are welcome.

The service is available at: [https://ogp.fly.dev](https://ogp.fly.dev)  
The code is on GitHub: [https://github.com/vladkens/ogp](https://github.com/vladkens/ogp)

The service is currently running without any restrictions. There is also the option to run self-hosted version with `ghcr.io/vladkens/ogp` image.

To integrate this service into a static website, you just need to add corresponding `<meta>` tags with service link and replace token with your data.

```html
<meta
  property="og:image"
  content="https://ogp.fly.dev/v0/png?title={title}&author={author}&photo={photo}&url={url}&theme={theme}"
/>
```

Usage example for this blog: [link generation](https://github.com/vladkens/blog/blob/ae18520/templates/base.html#L21), [meta tags](https://github.com/vladkens/blog/blob/ae18520/templates/base.html#L44). To see link sharing at work click on links below ⬇️💀
