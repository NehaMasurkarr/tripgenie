import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/destination.dart';

class ApiException implements Exception {
  final String message;
  const ApiException(this.message);
  @override
  String toString() => message;
}

class ApiClient {
  static const defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:5001',
  );
  final String baseUrl;
  final http.Client _client;
  final Duration timeout;
  ApiClient({
    this.baseUrl = defaultBaseUrl,
    http.Client? client,
    this.timeout = const Duration(seconds: 15),
  }) : _client = client ?? http.Client();

  Future<Map<String, dynamic>> _request(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? query,
  }) async {
    final uri = Uri.parse('$baseUrl$path').replace(queryParameters: query);
    try {
      final response =
          await (body == null
                  ? _client.get(uri)
                  : _client.post(
                      uri,
                      headers: {'Content-Type': 'application/json'},
                      body: jsonEncode(body),
                    ))
              .timeout(timeout);
      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw ApiException(
          (decoded['error'] as Map<String, dynamic>?)?['message'] as String? ??
              'The request could not be completed.',
        );
      }
      return decoded;
    } on TimeoutException {
      throw const ApiException('The request took too long. Please try again.');
    } on http.ClientException {
      throw const ApiException(
        'Cannot reach TripGenie. Check your connection and try again.',
      );
    } on FormatException {
      throw const ApiException('The server returned an unexpected response.');
    } on TypeError {
      throw const ApiException('The server returned an unexpected response.');
    }
  }

  Future<Map<String, dynamic>> options() async =>
      (await _request('/api/v1/options'))['data'] as Map<String, dynamic>;
  Future<DiscoveryPage> discover({
    String query = '',
    String? state,
    String? interest,
    int page = 1,
  }) async {
    final response = await _request(
      '/api/v1/destinations',
      query: {
        'page': '$page',
        'limit': '12',
        if (query.trim().isNotEmpty) 'q': query.trim(),
        if (state != null) 'state': state,
        if (interest != null) 'interest': interest,
      },
    );
    return DiscoveryPage(
      (response['data'] as List)
          .map((v) => Destination.fromJson(v as Map<String, dynamic>))
          .toList(),
      ((response['meta'] as Map<String, dynamic>)['total'] as num).toInt(),
    );
  }

  Future<Map<String, dynamic>> detail(int id) async =>
      (await _request('/api/v1/destinations/$id'))['data']
          as Map<String, dynamic>;
  Future<List<Recommendation>> recommend(
    Map<String, dynamic> preferences,
  ) async {
    final response = await _request(
      '/api/v1/recommendations',
      body: preferences,
    );
    return (response['data'] as List)
        .map((v) => Recommendation.fromJson(v as Map<String, dynamic>))
        .toList();
  }

  Future<TripPlan> itinerary(
    int id,
    int days,
    String tier,
    List<String> interests,
  ) async => TripPlan(
    (await _request(
          '/api/v1/itineraries',
          body: {
            'destination_id': id,
            'days': days,
            'budget_tier': tier,
            'interests': interests,
          },
        ))['data']
        as Map<String, dynamic>,
  );
  void close() => _client.close();
}
