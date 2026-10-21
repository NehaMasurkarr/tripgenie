import 'package:flutter/material.dart';
import '../models/destination.dart';
import '../widgets/brand.dart';

class ItineraryView extends StatelessWidget {
  final TripPlan plan;
  const ItineraryView({super.key, required this.plan});
  @override
  Widget build(BuildContext context) {
    final cost = plan.data['estimated_cost'] as Map<String, dynamic>;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeading(
          eyebrow: 'Your trip, taking shape',
          title: plan.name,
          subtitle:
              '${plan.days.length} days · Estimated local cost ${money(cost['low'] as num)}–${money(cost['high'] as num)} · ${label(cost['tier'] as String)}',
        ),
        Card(
          color: const Color(0xFFE8F0E5),
          margin: const EdgeInsets.only(bottom: 24),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'A flexible starting point',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                ...plan.warnings.map(
                  (w) => Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Text(w, style: const TextStyle(height: 1.5)),
                  ),
                ),
              ],
            ),
          ),
        ),
        ...plan.days.map(
          (day) => Card(
            margin: const EdgeInsets.only(bottom: 16),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: teal,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      '${day['day']}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'DAY ${day['day']}',
                          style: const TextStyle(
                            color: teal,
                            fontSize: 11,
                            letterSpacing: 1.5,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          day['title'] as String,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 10),
                        ...List<String>.from(day['attractions'] as List).map(
                          (a) => Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Text('• $a'),
                          ),
                        ),
                        ...List<String>.from(day['activities'] as List).map(
                          (a) => Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Text('Try: $a'),
                          ),
                        ),
                        if ((day['attractions'] as List).isEmpty &&
                            (day['activities'] as List).isEmpty)
                          const Text(
                            'Leave room for rest or choose an activity after checking local availability.',
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        ExpansionTile(
          title: const Text('Original catalogue itinerary'),
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(plan.data['source_itinerary'] as String),
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.only(top: 16),
          child: Text(
            'Before you go: ${plan.data['considerations']}\nPermits: ${plan.data['permits']}',
            style: const TextStyle(height: 1.6),
          ),
        ),
      ],
    );
  }
}
