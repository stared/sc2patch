import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ProcessedPatchData, ViewMode, Unit } from '../types';
import { groupUnitsByRace } from '../utils/dataLoader';

interface PatchGridProps {
  patches: ProcessedPatchData[];
  units: Map<string, Unit>;
  viewMode: ViewMode;
}

export function PatchGrid({ patches, units, viewMode }: PatchGridProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    unit: string;
    changes: string[];
    visible: boolean;
  }>({ x: 0, y: 0, unit: '', changes: [], visible: false });

  useEffect(() => {
    if (!svgRef.current || patches.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Get all units that have changes
    const allChangedUnits = new Set<string>();
    patches.forEach(patch => {
      patch.entities.forEach((_, entityId) => {
        allChangedUnits.add(entityId);
      });
    });

    const unitsByRace = groupUnitsByRace(allChangedUnits, units);
    const allUnits = [...unitsByRace.terran, ...unitsByRace.protoss, ...unitsByRace.zerg];

    const margin = { top: 80, right: 20, bottom: 20, left: 120 };
    const cellSize = 54;
    const cellPadding = 3;

    const width = margin.left + margin.right + allUnits.length * cellSize;
    const height = margin.top + margin.bottom + patches.length * cellSize;

    svg.attr('width', width).attr('height', height);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    // Create scales
    const xScale = d3.scaleBand()
      .domain(allUnits)
      .range([0, allUnits.length * cellSize])
      .padding(0);

    const yScale = d3.scaleBand()
      .domain(patches.map(p => p.version))
      .range([0, patches.length * cellSize])
      .padding(0);

    // Add race headers
    const raceHeaders = [
      { race: 'terran', units: unitsByRace.terran, color: '#4a9eff' },
      { race: 'protoss', units: unitsByRace.protoss, color: '#ffd700' },
      { race: 'zerg', units: unitsByRace.zerg, color: '#c874e9' }
    ];

    let xOffset = 0;
    raceHeaders.forEach(({ race, units: raceUnits, color }) => {
      if (raceUnits.length > 0) {
        g.append('text')
          .attr('x', xOffset + (raceUnits.length * cellSize) / 2)
          .attr('y', -40)
          .attr('text-anchor', 'middle')
          .attr('fill', color)
          .attr('font-size', 16)
          .attr('font-weight', 'bold')
          .text(race.charAt(0).toUpperCase() + race.slice(1));

        xOffset += raceUnits.length * cellSize;
      }
    });

    // Add patch version labels
    g.append('g')
      .selectAll('text')
      .data(patches)
      .enter()
      .append('text')
      .attr('x', -10)
      .attr('y', (d) => yScale(d.version)! + cellSize / 2)
      .attr('text-anchor', 'end')
      .attr('fill', '#aaa')
      .attr('font-size', 12)
      .attr('dominant-baseline', 'middle')
      .text(d => d.version);

    // Add patch dates
    g.append('g')
      .selectAll('text')
      .data(patches)
      .enter()
      .append('text')
      .attr('x', -60)
      .attr('y', (d) => yScale(d.version)! + cellSize / 2)
      .attr('text-anchor', 'end')
      .attr('fill', '#666')
      .attr('font-size', 10)
      .attr('dominant-baseline', 'middle')
      .text(d => d.date.split('-').slice(0, 2).join('-'));

    // Create cells for units with changes
    const cells = g.append('g')
      .selectAll('g')
      .data(patches.flatMap(patch =>
        Array.from(patch.entities.entries()).map(([entityId, entity]) => ({
          patch: patch.version,
          entityId,
          entity,
          x: xScale(entityId)!,
          y: yScale(patch.version)!
        }))
      ))
      .enter()
      .append('g')
      .attr('transform', d => `translate(${d.x},${d.y})`);

    // Add unit images
    cells.append('image')
      .attr('x', cellPadding)
      .attr('y', cellPadding)
      .attr('width', cellSize - cellPadding * 2)
      .attr('height', cellSize - cellPadding * 2)
      .attr('href', d => `/assets/units/${d.entityId}.jpg`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .style('cursor', 'pointer')
      .on('error', function() {
        // Fallback to placeholder
        d3.select(this).attr('href', '/assets/units/placeholder.svg');
      })
      .on('mouseenter', function(event, d) {
        const [x, y] = d3.pointer(event, document.body);
        setTooltip({
          x,
          y,
          unit: units.get(d.entityId)?.name || d.entityId,
          changes: d.entity.changes,
          visible: true
        });
      })
      .on('mouseleave', () => {
        setTooltip(prev => ({ ...prev, visible: false }));
      });

    // Add transitions for view mode changes
    if (viewMode === 'by-unit') {
      // Group by unit instead of patch
      const unitGroups = new Map<string, { patches: string[], changes: string[][] }>();

      patches.forEach(patch => {
        patch.entities.forEach((entity, entityId) => {
          if (!unitGroups.has(entityId)) {
            unitGroups.set(entityId, { patches: [], changes: [] });
          }
          const group = unitGroups.get(entityId)!;
          group.patches.push(patch.version);
          group.changes.push(entity.changes);
        });
      });

      // Reorganize the visualization
      // This is a placeholder for the by-unit view transformation
      // You would implement the actual regrouping logic here
    }

  }, [patches, units, viewMode]);

  return (
    <>
      <svg ref={svgRef}></svg>
      {tooltip.visible && (
        <div
          className="tooltip"
          style={{
            left: tooltip.x + 10,
            top: tooltip.y - 10
          }}
        >
          <h4>{tooltip.unit}</h4>
          <ul>
            {tooltip.changes.map((change, i) => (
              <li key={i}>{change}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}