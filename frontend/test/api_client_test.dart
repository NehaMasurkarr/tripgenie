import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:tripgenie/services/api_client.dart';

String fixture(String name) =>
    File('test/fixtures/$name.json').readAsStringSync();

void main() {
  test(
    'decodes catalogue and transmits URL-encoded discovery filters',
    () async {
      final api = ApiClient(
        client: MockClient((request) async {
          expect(request.url.queryParameters['q'], 'Goa & beaches');
          expect(request.url.queryParameters['state'], 'Goa');
          return http.Response(
            fixture('catalogue'),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );
      final result = await api.discover(query: 'Goa & beaches', state: 'Goa');
      expect(result.destinations.length, 2);
      expect(result.destinations.first.name, isNotEmpty);
      api.close();
    },
  );
  test('sends preference JSON and decodes breakdown and itinerary', () async {
    final api = ApiClient(
      client: MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(request.headers['content-type'], 'application/json');
        if (request.url.path.endsWith('recommendations')) {
          expect(body['interests'], ['beach']);
          return http.Response(
            fixture('recommendations'),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        expect(body['destination_id'], 1);
        return http.Response(
          fixture('itinerary'),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      }),
    );
    final results = await api.recommend({
      'interests': ['beach'],
    });
    expect(results.length, 5);
    expect(results.first.breakdown['budget'], isNotNull);
    final plan = await api.itinerary(1, 3, 'budget', ['beach']);
    expect(plan.days.length, 3);
    expect(plan.warnings, isNotEmpty);
    api.close();
  });
  test('surfaces API error and handles malformed response', () async {
    final api = ApiClient(
      client: MockClient(
        (_) async =>
            http.Response('{"error":{"message":"Invalid budget"}}', 400),
      ),
    );
    await expectLater(
      api.options(),
      throwsA(
        isA<ApiException>().having(
          (e) => e.message,
          'message',
          'Invalid budget',
        ),
      ),
    );
    api.close();
    final broken = ApiClient(
      client: MockClient((_) async => http.Response('<html>', 200)),
    );
    await expectLater(broken.options(), throwsA(isA<ApiException>()));
    broken.close();
  });
  test('maps network and timeout failures to useful messages', () async {
    final offline = ApiClient(
      client: MockClient((_) async => throw http.ClientException('network')),
    );
    await expectLater(
      offline.options(),
      throwsA(
        isA<ApiException>().having(
          (e) => e.message,
          'message',
          contains('Cannot reach'),
        ),
      ),
    );
    offline.close();
    final slow = ApiClient(
      timeout: const Duration(milliseconds: 5),
      client: MockClient((_) async {
        await Future<void>.delayed(const Duration(milliseconds: 20));
        return http.Response(
          fixture('options'),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      }),
    );
    await expectLater(
      slow.options(),
      throwsA(
        isA<ApiException>().having(
          (e) => e.message,
          'message',
          contains('too long'),
        ),
      ),
    );
    slow.close();
  });
}
