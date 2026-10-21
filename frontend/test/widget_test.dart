import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:tripgenie/main.dart';
import 'package:tripgenie/services/api_client.dart';

String fixture(String name) =>
    File('test/fixtures/$name.json').readAsStringSync();

ApiClient mockApi({
  void Function(http.Request)? onRequest,
  bool emptyMatches = false,
}) => ApiClient(
  client: MockClient((request) async {
    onRequest?.call(request);
    final path = request.url.path;
    final name = path.endsWith('options')
        ? 'options'
        : path.endsWith('recommendations')
        ? 'recommendations'
        : path.endsWith('itineraries')
        ? 'itinerary'
        : path.contains('destinations/')
        ? 'detail'
        : 'catalogue';
    if (emptyMatches && name == 'recommendations') {
      return http.Response('{"data":[],"meta":{}}', 200);
    }
    return http.Response(
      fixture(name),
      200,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  }),
);

void main() {
  for (final width in [390.0, 768.0, 1440.0]) {
    testWidgets('discovery and preferences fit a ${width.toInt()}px viewport', (
      tester,
    ) async {
      tester.view.physicalSize = Size(width, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final api = mockApi();
      addTearDown(api.close);
      await tester.pumpWidget(TripGenieApp(api: api));
      await tester.pumpAndSettle();
      expect(find.text('TripGenie'), findsOneWidget);
      expect(find.text('Your next\nIndia story.'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('Find my next trip'));
      await tester.pumpAndSettle();
      expect(find.text('A trip that fits you.'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets('preferences request leads to unique matches and itinerary', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    var recommendationRequests = 0;
    final api = mockApi(
      onRequest: (r) {
        if (r.url.path.endsWith('recommendations')) {
          recommendationRequests++;
        }
      },
    );
    addTearDown(api.close);
    await tester.pumpWidget(TripGenieApp(api: api));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Find my next trip'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('recommendButton')));
    await tester.tap(find.byKey(const Key('recommendButton')));
    await tester.pumpAndSettle();
    expect(recommendationRequests, 1);
    expect(find.text('Your destination shortlist.'), findsOneWidget);
    await tester.ensureVisible(find.text('Plan trip').first);
    await tester.tap(find.text('Plan trip').first);
    await tester.pumpAndSettle();
    expect(find.text('DAY 1'), findsOneWidget);
    expect(find.text('DAY 3'), findsOneWidget);
    expect(find.text('A flexible starting point'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'budget validation prevents requests and empty matches are clear',
    (tester) async {
      tester.view.physicalSize = const Size(1200, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      var count = 0;
      final api = mockApi(
        emptyMatches: true,
        onRequest: (r) {
          if (r.url.path.endsWith('recommendations')) {
            count++;
          }
        },
      );
      addTearDown(api.close);
      await tester.pumpWidget(TripGenieApp(api: api));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Find my next trip'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('budgetInput')), '0');
      await tester.ensureVisible(find.byKey(const Key('recommendButton')));
      await tester.tap(find.byKey(const Key('recommendButton')));
      await tester.pumpAndSettle();
      expect(count, 0);
      expect(
        find.text('Enter a budget between ₹1 and ₹1,000,000'),
        findsOneWidget,
      );
      await tester.ensureVisible(find.byKey(const Key('budgetInput')));
      await tester.enterText(find.byKey(const Key('budgetInput')), '3000');
      await tester.ensureVisible(find.byKey(const Key('recommendButton')));
      await tester.tap(find.byKey(const Key('recommendButton')));
      await tester.pumpAndSettle();
      expect(count, 1);
      expect(find.text('Let’s open up the possibilities'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets('startup failure offers working retry', (tester) async {
    var failed = true;
    final api = ApiClient(
      client: MockClient((request) async {
        if (failed) {
          return http.Response(
            '{"error":{"message":"Temporarily offline"}}',
            503,
          );
        }
        return http.Response(
          fixture(
            request.url.path.endsWith('options') ? 'options' : 'catalogue',
          ),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      }),
    );
    addTearDown(api.close);
    await tester.pumpWidget(TripGenieApp(api: api));
    await tester.pumpAndSettle();
    expect(find.text('Let’s reconnect'), findsOneWidget);
    failed = false;
    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();
    expect(find.text('Find my next trip'), findsOneWidget);
  });
}
