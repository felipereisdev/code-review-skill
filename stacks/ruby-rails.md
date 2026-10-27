# Ruby / Ruby on Rails — Code Review Checklist

> Check sibling files for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that RuboCop or Brakeman, as the repository configures them, already reports is not a finding. The `## Ruby` section applies to every Ruby package. The `## Rails` sections apply only when the package's own `Gemfile` declares `rails` directly; a `Gemfile.lock` that lists Rails, or a gem that depends on part of it, never proves a Rails application. Read the Ruby version from `.ruby-version` or the `ruby` line of the `Gemfile`, and the Rails version from the `Gemfile` or `Gemfile.lock`; an item that names a version applies only to that version, and a Rails default applies only when `config.load_defaults` and the application's configuration keep it.

## Ruby

- **Commands through a shell**: backticks, `%x()`, and `system`, `exec`, `spawn`, `IO.popen` or `Open3.capture2` given one string run it through a shell when it contains shell characters, so input interpolated into that string runs commands. Pass the program and each argument separately (`system("convert", path, "out.png")`). Before Ruby 4.0, `Kernel#open` with a value that starts with `|` runs a command (deprecated in Ruby 3.3, removed in Ruby 4.0). Ruby 3.3 deprecated the same leading-`|` process creation for `URI.open`, `IO.read`, `IO.readlines`, `IO.write`, `IO.binread` and `IO.foreach`, and Ruby 4.0 removed the `IO` class-method forms. Use `File.open` for files. **Not a finding:** strings built only from constants, and a leading `|` on Ruby 4.0 or later, which is not command execution.
- **Unsafe deserialization**: `Marshal.load` of data that a user or another system controls can instantiate arbitrary objects and run code. `YAML.load` does the same with Psych before 4.0; Psych 4 (the default from Ruby 3.1) makes `YAML.load` safe and moves the old behavior to `YAML.unsafe_load`. **Not a finding:** `YAML.safe_load`, `JSON.parse` without `create_additions: true`, and `Marshal` data that only the application writes and reads.
- **Method or class names from input**: `send(params[:action])`, `public_send(name)` and `params[:type].constantize` let the caller choose which method runs or which class is loaded. Map the input to an allowlist of names first. `public_send` still reaches every public method, including `destroy` or `update`.
- **Line anchors in regular expressions**: `^` and `$` match at every line boundary in Ruby, so `/^\d+$/` accepts `"1\n<script>"`. Use `\A` and `\z` to match the whole string. Rails `validates ... format:` raises an error for a pattern with `^` or `$` unless `multiline: true` is set.

## Rails: Data Access

- **SQL fragments from input**: string conditions with interpolation (`where("email = '#{params[:email]}'")`), `find_by_sql`, `connection.execute`, and the arguments of `pluck`, `select`, `group`, `having`, `joins` and `order` built from input are SQL text. In Rails 6.0, `order` and `pluck` given a raw SQL string that the adapter's column-name matcher does not accept log a deprecation warning by default (`allow_unsafe_raw_sql` is `:deprecated`), and raise `ActiveRecord::UnknownAttributeReference` when it is `:disabled`. Rails 6.1 removed the warning path, so they raise in every configuration. `Arel.sql` only marks a string as author-trusted; it does not bind or sanitize input. A column name from input still lets the caller sort or read by any column, so map sort keys to a fixed list.
- **Records found outside the user's scope**: `Invoice.find(params[:id])` loads any invoice by ID. Report it when no authorization step checks the loaded record, such as `authorize @invoice` (Pundit), `load_and_authorize_resource` (CanCanCan) or a `before_action` that compares the owner. Scope the query instead: `current_user.invoices.find(params[:id])`. **Not a finding:** public records, and a policy check that runs on the loaded record before it is used.
- **N+1 queries**: a loop over records that reads an association (`order.customer.name`) without `includes`, `preload` or `eager_load` runs one query per record. **Not a finding:** a single record, an association already loaded, and `strict_loading` (Rails 6.1+), which raises instead of loading lazily.
- **Side effects before commit**: `after_save` and `after_create` callbacks run inside the transaction, so an email sent or a job enqueued there happens even when the transaction rolls back, and a job can run before the row is visible to it. Use `after_commit` (`after_create_commit`). Rails 7.2 added `enqueue_after_transaction_commit` for Active Job, and its default differs between releases and `config.load_defaults` versions: read the application's configuration before reporting an enqueue inside a transaction.

**Bad** — the email is interpolated into the SQL text, and any invoice ID is loaded:

```ruby
def show
  @user = User.where("email = '#{params[:email]}'").first
  @invoice = Invoice.find(params[:id])
end
```

**Good** — the value is bound, and the lookup is scoped to the current user:

```ruby
def show
  @user = User.find_by(email: params[:email])
  @invoice = current_user.invoices.find(params[:id])
end
```

**Bad** — the email is sent inside the transaction, even when the transaction later rolls back:

```ruby
class Order < ApplicationRecord
  after_create :send_confirmation

  def send_confirmation
    OrderMailer.confirmation(self).deliver_now
  end
end
```

**Good** — the email is enqueued only after the row is committed:

```ruby
class Order < ApplicationRecord
  after_create_commit :send_confirmation

  def send_confirmation
    OrderMailer.confirmation(self).deliver_later
  end
end
```

## Rails: Controllers, Views and Jobs

- **Open redirects**: `redirect_to params[:return_to]` sends the user to any host. Rails 7.0 added `raise_on_open_redirects`, which `load_defaults 7.0` sets to `true`. From Rails 8.1, `action_on_open_redirect` (`:raise`, `:log` or `:notify`) controls this instead: `load_defaults 7.0` sets it to `:raise`, its built-in default is `:log` (the redirect happens), and `raise_on_open_redirects = true` still forces a raise. Report a redirect target from input unless the effective setting raises (`raise_on_open_redirects` is `true`, or `action_on_open_redirect` is `:raise`) and the call does not pass `allow_other_host: true`. A call that passes `allow_other_host: true` is reportable only when an untrusted external host can actually reach it. **Not a finding:** input validated as a relative path or a same-host URL before the redirect.
- **Mass assignment with `permit!`**: `params.permit!`, `params.to_unsafe_h` or a permit list that includes `role`, `admin` or an owner ID lets the caller set those attributes.
- **Jobs that are not idempotent**: Sidekiq and most Active Job backends deliver a job at least once and retry it after an error, so a job that charges a card or sends an email and then fails later runs that step again. Report a job that repeats an external effect on retry with no idempotency key or state check. A job that receives an Active Record object gets it through GlobalID and raises `ActiveJob::DeserializationError` when the record was deleted before the job ran.

## Conventions, not defects

- Service objects, concerns, form objects, `before_action` placement, the choice between Pundit and CanCanCan, and query object layout follow the repository's conventions.
- RuboCop style cops that the repository does not enable, and `find_each` for small, bounded collections, are not findings.

## Sources

- Rails security guide (SQL injection, CSRF, redirects, mass assignment): https://guides.rubyonrails.org/security.html
- Active Record querying and eager loading: https://guides.rubyonrails.org/active_record_querying.html; raw SQL in `order` and `pluck`: Rails 6.1 release notes, Active Record removals, https://guides.rubyonrails.org/6_1_release_notes.html; Rails 6.0 `allow_unsafe_raw_sql` default and warning: https://raw.githubusercontent.com/rails/rails/v6.0.0/activerecord/lib/active_record/core.rb and https://raw.githubusercontent.com/rails/rails/v6.0.0/activerecord/lib/active_record/sanitization.rb; Rails 6.1 raise: https://raw.githubusercontent.com/rails/rails/v6.1.0/activerecord/lib/active_record/sanitization.rb; `order` and `pluck` call sites: https://raw.githubusercontent.com/rails/rails/v6.0.0/activerecord/lib/active_record/relation/query_methods.rb and https://raw.githubusercontent.com/rails/rails/v6.0.0/activerecord/lib/active_record/relation/calculations.rb
- Callbacks and transactions: https://guides.rubyonrails.org/active_record_callbacks.html#transaction-callbacks; Active Job: https://guides.rubyonrails.org/active_job_basics.html
- Strong parameters and forgery protection: https://guides.rubyonrails.org/action_controller_overview.html; `raise_on_open_redirects` and `action_on_open_redirect` with framework defaults: https://guides.rubyonrails.org/configuring.html (sections 3.9.17–3.9.18); Rails 8.1 redirect handling: https://raw.githubusercontent.com/rails/rails/v8.1.0/actionpack/lib/action_controller/metal/redirecting.rb; Rails 8.1 `load_defaults 7.0`: https://raw.githubusercontent.com/rails/rails/v8.1.0/railties/lib/rails/application/configuration.rb; Rails 7.0 `load_defaults 7.0`: https://raw.githubusercontent.com/rails/rails/v7.0.0/railties/lib/rails/application/configuration.rb
- Action View escaping: https://guides.rubyonrails.org/action_view_overview.html; `render html:` escaping: https://guides.rubyonrails.org/layouts_and_rendering.html and https://raw.githubusercontent.com/rails/rails/v7.0.0/actionview/lib/action_view/template/html.rb; format validation anchors: https://guides.rubyonrails.org/active_record_validations.html#format
- Ruby `Kernel#system` and regular expression anchors: https://docs.ruby-lang.org/en/master/Kernel.html, https://docs.ruby-lang.org/en/master/Regexp.html; leading-`|` process creation: Ruby 3.3 NEWS, https://raw.githubusercontent.com/ruby/ruby/v3_3_0/NEWS.md, and Ruby 4.0 NEWS, https://raw.githubusercontent.com/ruby/ruby/v4.0.0/NEWS.md; `Marshal`: https://docs.ruby-lang.org/en/master/Marshal.html; Psych 4: Ruby 3.1 NEWS, https://raw.githubusercontent.com/ruby/ruby/v3_1_0/NEWS.md, and Psych v4.0.0 release, https://github.com/ruby/psych/releases/tag/v4.0.0
- Sidekiq retries and idempotency: https://github.com/sidekiq/sidekiq/wiki/Best-Practices

## Precedents

- **Active Record binds hash and placeholder conditions**: `where(email: value)`, `where("email = ?", value)`, `find`, `find_by(email: value)`, `create` and `update` quote or bind their values. Do not report SQL injection for values passed that way. **Exception:** string conditions with interpolation, `find_by_sql`, `connection.execute`, `Arel.sql` around input, and arguments of `pluck`, `select`, `group`, `having`, `joins` or `order` built from input, including column names.
- **ERB `<%= %>` escapes strings**: in a Rails view, `<%= value %>` HTML-escapes a string that is not marked `html_safe`. Do not report XSS for such values rendered with `<%= %>`. **Exception:** `raw`, `.html_safe`, `<%== %>`, `render html:` with input marked `html_safe`, `render inline:` with input (the input is evaluated as an ERB template, so it is code execution, not only unescaped output), helpers that mark their output safe without escaping it, values inside `<script>` blocks and event-handler attributes, and user-controlled URLs in `href` or `src`, such as `link_to` with a `javascript:` URL.
- **Strong parameters stop unpermitted mass assignment**: passing an `ActionController::Parameters` object that was not permitted to `new`, `create`, `update` or `assign_attributes` raises `ActiveModel::ForbiddenAttributesError`, and `permit` drops every key it does not list. Do not report mass assignment of attributes that the permit list does not include. **Exception:** `permit!`, `to_unsafe_h`, permit lists that include privileged attributes such as `role`, `admin` or an owner ID, and hashes built from the request body some other way.
- **Controllers check CSRF tokens by default**: since Rails 5.2, a controller that inherits from `ActionController::Base` verifies the authenticity token on requests other than `GET` and `HEAD`. Do not report missing CSRF protection on such a controller. **Exception:** `skip_forgery_protection` or `skip_before_action :verify_authenticity_token`, `protect_from_forgery with: :null_session` for cookie-authenticated requests, controllers that inherit from `ActionController::API` and still authenticate with cookies, `default_protect_from_forgery = false`, and state changes on `GET` routes.
