typedef Json = Map<String, dynamic>;

class ContentItem {
  const ContentItem({
    required this.id,
    required this.title,
    required this.body,
    this.demo = false,
  });
  final String id, title, body;
  final bool demo;
  factory ContentItem.fromJson(Json json) => ContentItem(
    id: json['id'] as String,
    title: json['title'] as String,
    body: json['body'] as String? ?? '',
    demo: json['demo'] == true,
  );
}

class ApiPage {
  const ApiPage(this.items, this.total, {this.page = 1, this.pageSize = 20});
  final List<Json> items;
  final int total;
  final int page, pageSize;
  factory ApiPage.fromJson(Json json) => ApiPage(
    (json['items'] as List).map((e) => Json.from(e as Map)).toList(),
    json['total'] as int,
    page: json['page'] as int? ?? 1,
    pageSize: json['page_size'] as int? ?? 20,
  );
}
