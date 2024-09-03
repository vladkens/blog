---
title: Table sorting and pagination with HTMX
slug: htmx-table-sorting
date: 2024-08-18
taxonomies:
  tags: ["tutorial", "rust", "htmx", "webdev"]
extra:
  medium: https://medium.com/p/7af8416f2b30
  devto: https://dev.to/vladkens/table-sorting-and-pagination-with-htmx-3dh8
---

I recently tried HTMX for my new project – [ghstats](https://github.com/vladkens/ghstats) – a dashboard of Github repository traffic in a single interface for longer than 14 days. This project was planned as a self-hosted service, so I was thinking about a really simple and memory-less tech stack. Last time I played with Rust, so I decided to use it instead of NodeJS / Python. Of course, if I'm generating static HTML on the server side, I have two options for implementing table sorting and pagination: use query parameters and do everything on backend, or use some JavaScript to call data from the backend and render the table on the client side. But HTMX offers a new, third way: write all the logic on the backend and replace the necessary parts of HTML with just a few tag attributes. Let's see how it works.

## Initial setup

To demonstrate table sorting and pagination, I'll be using the same stack I used for my service: `axum` as a backend framework and `maud` for HTML templating (it's a DSL over Rust templates).

Let's create new project with:

```sh
cargo init htmx-example && cd-html-example
```

Then install dependencies:

```sh
cargo add tokio axum maud --features tokio/full,maud/axum
```

and do initial setup in `src/main.rs` file:

```rust
use axum::{response::IntoResponse, routing::get, Router};
use maud::html;

async fn index_page() -> impl IntoResponse {
  html! {
    h1 { "Hello, World!" }
  }
}

#[tokio::main]
async fn main() {
  let service = Router::new().route("/", get(index_page)).into_make_service();
  let listener = tokio::net::TcpListener::bind("127.0.0.1:8080").await.unwrap();
  axum::serve(listener, service).await.unwrap();
}
```

Then we cant run this with `cargo watch -x run` and open `http://127.0.0.1:8080` in the browser. "Hello, World!" should be displayed.

## Creating a static table

Let's add crates to generate random data:

```sh
cargo add fake rand rand_chacha --features fake/derive
```

and define simple `Contact` struct (like our application is simple CMS).

```rust
use fake::faker::company::en::*;
use fake::faker::internet::en::*;
use fake::faker::name::en::*;
use fake::faker::phone_number::en::*;
use fake::{Dummy, Fake, Faker};
use rand::prelude::*;
use rand_chacha::ChaCha8Rng;

#[derive(Debug, Clone, Dummy)]
struct Contact {
  id: u64,

  #[dummy(faker = "Name()")]
  name: String,

  #[dummy(faker = "CompanyName()")]
  company: String,

  #[dummy(faker = "FreeEmail()")]
  email: String,

  #[dummy(faker = "PhoneNumber()")]
  phone: String,
}

fn get_contacts(n: usize) -> Vec<Contact> {
  let mut items = Vec::with_capacity(n);
  let mut rng = ChaCha8Rng::seed_from_u64(42);
  for _ in 0..n {
    items.push(Faker.fake_with_rng(&mut rng));
  }
  items
}

async fn index_page() -> impl IntoResponse {
	let contacts = get_contacts(100);
	println!(">> {:?}", contacts[0]);
	println!(">> {:?}", contacts[1]);

  html! {
    h1 { "Hello, World!" }
  }
}
```

Now on each request same random contacts will be generated, so we can use this data in our table.
`get_contacts` function emulates database query in real environment.

I will also add base layout for page with [PicoCSS](https://picocss.com/) framework to have nice look:

```rust
fn base(html: maud::Markup) -> impl IntoResponse {
  html! {
    html {
      head {
        meta charset="utf-8" {}
        title { "Contacts" }

        link rel="stylesheet" href="https://unpkg.com/@picocss/pico@2.0" {}
        script src="https://unpkg.com/htmx.org@2.0" {}
      }
      body class="container" {
        { (html) }
      }
    }
  }
}
```

And finally update `index_page` to render contact table:

```rust
async fn index_page() -> impl IntoResponse {
  let contacts = get_contacts(100);

  base(html! {
    table {
      thead {
        tr {
          th { "ID" }
          th { "Name" }
          th { "Company" }
          th { "Email" }
          th { "Phone" }
        }
      }
      tbody {
        @for contact in contacts {
          tr {
            td { (contact.id) }
            td { (contact.name) }
            td { (contact.company) }
            td { (contact.email) }
            td { (contact.phone) }
          }
        }
      }
    }
  })
}
```

We can request again `http://127.0.0.1:8080` and see our table with random contacts (which on each request at same).

## Sorting table

Now is the time to add sorting to our table. We will use HTMX to send requests to the server and get sorted HTML back. First, we need to add sorting logic to our backend. We will use query parameters to pass sorting column and direction.

To make it easier, I will add struct `TableFilter` which will represent sorting and pagination parameters, for code simplicity I will parse Request manually rather than using `Query` extractor and `serde` crate:

```rust
use std::collections::HashMap;
use axum::extract::{Query, Request};

#[derive(Debug)]
struct TableFilter {
  sort: String,
  order: String,
  page: u32,
  per_page: u32,
}

fn parse_table_filter(req: &Request) -> TableFilter {
  let qs: Query<HashMap<String, String>> = Query::try_from_uri(req.uri()).unwrap();
  let sort = qs.get("sort").unwrap_or(&"name".to_string()).to_string();
  let order = qs.get("order").unwrap_or(&"desc".to_string()).to_string();
  let page = qs.get("page").unwrap_or(&"1".to_string()).parse().unwrap();
  let per_page = qs.get("per_page").unwrap_or(&"10".to_string()).parse().unwrap();
  TableFilter { sort, order, page, per_page }
}

```

Next, we need to create a function to render `th` with HTMX attributes to handle sorting:

```rust

fn th(title: &str, qs: &TableFilter) -> maud::Markup {
  let id = title.to_lowercase();
  let order = if qs.sort == id && qs.order == "desc" { "asc" } else { "desc" };
  let url = format!("/?sort={}&order={}&page=1&per_page={}", id, order, qs.per_page);

  html! {
    th scope="col" style="cursor: pointer;"
      hx-trigger="click"
      hx-get=(url)
      hx-target="#contacts_table"
      hx-swap="outerHTML"
    {
      (title)
      @if qs.sort == id {
        span style="margin-left: 0.5em;" {
          @if qs.order == "asc" { "↑" } @else { "↓" }
        }
      }
    }
  }
}
```

Update `get_contacts` to accept `TableFilter` and sort items / do pagination:

```rust

fn get_contacts(n: usize, qs: &TableFilter) -> (Vec<Contact>, u32) {
  let mut items: Vec<Contact> = Vec::with_capacity(n);
  let mut rng = ChaCha8Rng::seed_from_u64(42);
  for _ in 0..n {
    items.push(Faker.fake_with_rng(&mut rng));
  }

  items.sort_by(|a, b| {
    let cmp = match qs.sort.as_str() {
      "id" => a.id.cmp(&b.id),
      "name" => a.name.cmp(&b.name),
      "company" => a.company.cmp(&b.company),
      "email" => a.email.cmp(&b.email),
      "phone" => a.phone.cmp(&b.phone),
      _ => a.id.cmp(&b.id),
    };

    if qs.order == "asc" {
      cmp
    } else {
      cmp.reverse()
    }
  });

  let pages = (items.len() as f64 / qs.per_page as f64).ceil() as u32;
  let range_s = (qs.page as usize - 1) * qs.per_page as usize;
  let range_e = qs.page as usize * qs.per_page as usize;
  let items = items[range_s..range_e].to_vec();

  (items, pages)
}
```

And finally, we can update our `index_page` to use `TableFilter` and `th`:

```rust
async fn index_page(req: Request) -> impl IntoResponse {
  let qs = parse_table_filter(&req);
  let (contacts, pages) = get_contacts(100, &qs);

  base(html! {
  	// id added to tell HTMX where to put new data
    table id="contacts_table" {
      thead {
        tr {
          (th("ID", &qs))
          (th("Name", &qs))
          (th("Company", &qs))
          (th("Email", &qs))
          (th("Phone", &qs))
        }
      }
      // same as before
    }
  })
}
```

That's it! Now we can sort our table by clicking on the column header. HTMX will send a request to the server with sorting parameters and replace the table with the new sorted data. Let's me explain HTMX attributes:

- `hx-trigger` - event which will trigger the request, in our case it's `click`
- `hx-get` - URL to send the request and HTTP method (can be GET or POST)
- `hx-target` - CSS selector to replace with new data
- `hx-swap` - how to replace the target, in our case it's `outerHTML` which will replace the whole table (by default it's inserting new data into the target)

All this attributes handled automatically by HTMX, so we just need to include HTMX script in `<head>`.

## Pagination

In previous step we already parse pagination filters to struct, so lets add code to render pagination links. I will use code from my another `react` project, which originally from StackOverflow answer:

```rust
// https://stackoverflow.com/a/70263913
fn calc_pagination(page: usize, total: usize, len: usize) -> Vec<Option<usize>> {
  use std::cmp::{max, min};

  let len = if len == 0 { 5 } else { len };
  let total = max(total, page);
  let start =
    max(1, min(page as isize - ((len - 3) as isize / 2), total as isize - len as isize + 2))
      as usize;
  let end = min(total, max(page + (len - 2) / 2, len - 1));

  let mut result = Vec::new();

  if start > 2 {
    result.push(Some(1));
    result.push(None);
  } else if start > 1 {
    result.push(Some(1));
  }

  for i in start..=end {
    result.push(Some(i));
  }

  if end < total - 1 {
    result.push(None);
    result.push(Some(total));
  } else if end < total {
    result.push(Some(total));
  }

  result
}
```

Let's define two more helper function which will render pagination link and delimiter (like `...`):

```rust
fn pagination_link(qs: &TableFilter, i: u32) -> maud::Markup {
  let url = format!("/?sort={}&order={}&page={}&per_page={}", qs.sort, qs.order, i, qs.per_page);
  html! {
    li {
      a href=(url)
        hx-trigger="click"
        hx-get=(url)
        hx-target="#contacts_table"
        hx-swap="outerHTML"
      { (i) }
    }
  }
}

fn pagination_delim() -> maud::Markup {
  html! {
    li {
      span { "..." }
    }
  }
}
```

And finally we can write pagination function, which will return list of links and delimiters:

```rust
fn pagination(pages: u32, qs: &TableFilter) -> maud::Markup {
  let items = calc_pagination(qs.page as usize, pages as usize, 5);

  html!(
    nav {
      ul {
        @for item in items {
          @if let Some(i) = item {
            (pagination_link(qs, i as u32))
          } @else {
            (pagination_delim())
          }
        }
      }
    }
  )
}

async fn index_page(req: Request) -> impl IntoResponse {
	// ...
	base(html! {
		// ..
		// add pagination call after table
		(pagination(pages, &qs))
	})
}
```

## Partial HTML updates

Before this step, we always replaced the whole page with new HTML content. This can be done without HTMX at all, so what the point of using it? It's right, we have very simple layout before. Let's make it more complex to show nice feature of HTMX – partial updates.

First of all let's move table generation into separate function:

```rust
fn get_contacts_table(contacts: Vec<Contact>, qs: &TableFilter, pages: u32) -> maud::Markup {
  html! {
  	// id moved from table to div
  	div id="contacts_table" {
	    table {
	      thead {
	        tr {
	          (th("ID", &qs))
	          (th("Name", &qs))
	          (th("Company", &qs))
	          (th("Email", &qs))
	          (th("Phone", &qs))
	        }
	      }
	      tbody {
	        @for contact in contacts {
	          tr {
	            td { (contact.id) }
	            td { (contact.name) }
	            td { (contact.company) }
	            td { (contact.email) }
	            td { (contact.phone) }
	          }
	        }
	      }
	    }

	    (pagination(pages, &qs))
   	}
  }
}
```

Now we can call this code in any other place and have contacts table. Now let's add some navigation and other content to our main page:

```rust
async fn index_page(req: Request) -> impl IntoResponse {
  let qs = parse_table_filter(req);
  let (contacts, pages) = get_contacts(1000, &qs);

  base(html! {
    nav {
      ul {
        li { a href="/dashboard" { "Dashboard" } }
        li { a href="/" { "Contacts" } }
        li { a href="/settings" { "Settings" } }
      }
    }

    h1 { "Contacts" }
    (get_contacts_table(contacts, &qs, pages))
  })
}
```

Right now in the application we have a simple navigation. But when we interact with the table, a full page will be returned, and the result will look like a nested page in a nested page... This is wrong. Let's fix this with HTMX (and this is actually where HTMX comes power).

When browser loads the page it load as regular page with default headers. When request send by HTMX it will set extra headers like `HX-Request` and `HX-Target`. We can use this headers to detect which part of HTML should be returned. Let's add this code to our `index_page`:

```rust
fn get_hx_target(req: &Request) -> Option<&str> {
  match req.headers().get("hx-target") {
    Some(x) => Some(x.to_str().unwrap_or_default()),
    None => None,
  }
}

async fn index_page(req: Request) -> impl IntoResponse {
  let qs = parse_table_filter(&req);
  let (contacts, pages) = get_contacts(1000, &qs);

  match get_hx_target(&req) {
    Some("contacts_table") => return get_contacts_table(contacts, &qs, pages).into_response(),
    _ => {}
  }

  base(html! {
  	// ... this part is the same
  })
  .into_response() // added into_response() to relax rust type inference
}
```

So in this code we check if `hx-target` header is present. If not – we return full page. If it's present and equal to `contacts_table` – we return only table. This is how partial updates works in HTMX. We can split page to smaller parts and update it independently.

Full code from this article can be found [here](https://github.com/vladkens/blog_code/tree/main/rust-htmx-table-sorting).

## Conclusion

HTMX is good utility for simple application which allows to add some interactivity without writing a lot of JavaScript code. It easy to use and can be integrated with any backend language, because not require any special server-side support. It's also very lightweight and can be used in any project without any additional dependencies.
