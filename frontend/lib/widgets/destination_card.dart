import 'package:flutter/material.dart';
import '../models/destination.dart';
import 'brand.dart';

class DestinationCard extends StatelessWidget {
  final Destination destination;
  final Recommendation? recommendation;
  final VoidCallback onExplore;
  final VoidCallback onPlan;
  const DestinationCard({
    super.key,
    required this.destination,
    this.recommendation,
    required this.onExplore,
    required this.onPlan,
  });
  @override
  Widget build(BuildContext context) => Card(
    clipBehavior: Clip.antiAlias,
    margin: EdgeInsets.zero,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 140,
          child: Stack(
            children: [
              Positioned.fill(
                child: Landscape(interests: destination.interests),
              ),
              Positioned(
                top: 12,
                left: 12,
                right: 12,
                child: Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _badge(destination.region),
                    if (recommendation != null)
                      _badge(
                        'Match · ${(recommendation!.score * 100).round()} / 100',
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                destination.state.toUpperCase(),
                style: const TextStyle(
                  fontSize: 10,
                  letterSpacing: 1.3,
                  color: teal,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 7),
              Tooltip(
                message: destination.name,
                child: Text(
                  destination.name,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 21,
                    fontFamily: 'Georgia',
                    fontWeight: FontWeight.w600,
                    color: ink,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Text(
                destination.description,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(height: 1.45, color: Color(0xFF586C65)),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 6,
                runSpacing: 5,
                children: destination.interests
                    .take(3)
                    .map((t) => _badge(label(t)))
                    .toList(),
              ),
              const SizedBox(height: 16),
              Text(
                '${money(destination.costLow)}–${money(destination.costHigh)} / day',
                style: const TextStyle(fontWeight: FontWeight.w700, color: ink),
              ),
              Text(
                '${destination.idealDays.toString().replaceAll('.0', '')} ideal days · ${destination.accessibility} access',
                style: const TextStyle(fontSize: 12, color: Color(0xFF586C65)),
              ),
              if (recommendation != null)
                ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  title: const Text(
                    'Why this match?',
                    style: TextStyle(fontSize: 13),
                  ),
                  children: [
                    ...recommendation!.breakdown.entries.map((entry) {
                      final values = entry.value as Map<String, dynamic>;
                      const names = {
                        'content': 'Similar experiences',
                        'popularity': 'Popularity',
                        'interests': 'Your interests',
                        'budget': 'Budget fit',
                        'season': 'Season match',
                        'duration': 'Trip length',
                      };
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          children: [
                            Expanded(
                              child: Text(
                                names[entry.key] ?? label(entry.key),
                                style: const TextStyle(fontSize: 12),
                              ),
                            ),
                            Text(
                              '${((values['score'] as num) * 100).round()} / 100',
                              style: const TextStyle(fontSize: 12),
                            ),
                          ],
                        ),
                      );
                    }),
                    const Text(
                      'A catalogue match score, not a guarantee of suitability.',
                      style: TextStyle(fontSize: 11),
                    ),
                  ],
                ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: onExplore,
                      child: const Text('Explore'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: FilledButton(
                      onPressed: onPlan,
                      child: const Text('Plan trip'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    ),
  );
  Widget _badge(String text) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: const Color(0xFFEFF4EB),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(text, style: const TextStyle(fontSize: 10, color: ink)),
  );
}

class DestinationGrid extends StatelessWidget {
  final List<Destination> destinations;
  final List<Recommendation>? recommendations;
  final ValueChanged<Destination> onExplore;
  final ValueChanged<Destination> onPlan;
  const DestinationGrid({
    super.key,
    required this.destinations,
    this.recommendations,
    required this.onExplore,
    required this.onPlan,
  });
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final columns = constraints.maxWidth < 640
          ? 1
          : constraints.maxWidth < 1000
          ? 2
          : 3;
      final width = (constraints.maxWidth - (columns - 1) * 20) / columns;
      return Wrap(
        spacing: 20,
        runSpacing: 20,
        children: List.generate(
          destinations.length,
          (i) => SizedBox(
            width: width,
            child: DestinationCard(
              destination: destinations[i],
              recommendation: recommendations?[i],
              onExplore: () => onExplore(destinations[i]),
              onPlan: () => onPlan(destinations[i]),
            ),
          ),
        ),
      );
    },
  );
}
