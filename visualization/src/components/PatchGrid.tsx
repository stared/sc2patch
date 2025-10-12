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
    const allUnits = [...unitsByRace.terran, ...unitsByRace.zerg, ...unitsByRace.protoss];  // Fixed order

    const margin = { top: 80, right: 20, bottom: 20, left: 120 };
    const cellSize = 54;
    const cellPadding = 3;

    // For compact view, calculate actual positions based on changes per patch
    let maxUnitsInPatch = 0;
    if (viewMode === 'by-patch') {
      // Calculate max units in any patch for width
      patches.forEach(patch => {
        let unitCount = 0;
        patch.entities.forEach(entity => {
          if (entity.type === 'unit') unitCount++;
        });
        maxUnitsInPatch = Math.max(maxUnitsInPatch, unitCount);
      });

      // Width includes unit section + space + upgrade columns (4 races * 150px each)
      const width = margin.left + margin.right + Math.max(maxUnitsInPatch, 10) * cellSize + 50 + (4 * 150);
      const height = margin.top + margin.bottom + patches.length * cellSize;

      svg.attr('width', width).attr('height', height);
    } else {
      const width = margin.left + margin.right + allUnits.length * cellSize;
      const height = margin.top + margin.bottom + patches.length * cellSize;

      svg.attr('width', width).attr('height', height);
    }

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

    // Add race headers (corrected order)
    const raceHeaders = [
      { race: 'terran', units: unitsByRace.terran, color: '#4a9eff' },
      { race: 'zerg', units: unitsByRace.zerg, color: '#c874e9' },      // Zerg second
      { race: 'protoss', units: unitsByRace.protoss, color: '#ffd700' }  // Protoss third
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

    // Add clickable patch version labels
    const patchLinks = g.append('g')
      .selectAll('a')
      .data(patches)
      .enter()
      .append('a')
      .attr('href', d => d.url)
      .attr('target', '_blank')
      .attr('rel', 'noopener noreferrer');

    patchLinks.append('text')
      .attr('x', -10)
      .attr('y', (d) => yScale(d.version)! + cellSize / 2)
      .attr('text-anchor', 'end')
      .attr('fill', '#4a9eff')
      .attr('font-size', 12)
      .attr('dominant-baseline', 'middle')
      .style('cursor', 'pointer')
      .style('text-decoration', 'underline')
      .text(d => d.version)
      .on('mouseenter', function() {
        d3.select(this).attr('fill', '#6ab7ff');
      })
      .on('mouseleave', function() {
        d3.select(this).attr('fill', '#4a9eff');
      });

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

    // Collect all cells (units, upgrades, buildings) organized by race
    const allCells: any[] = [];

    if (viewMode === 'by-patch') {
      // Compact view: show all changes grouped by race
      patches.forEach(patch => {
        const cellsByRace = { terran: [], zerg: [], protoss: [], neutral: [] } as any;

        // Group all entities by race
        patch.entities.forEach((entity, entityId) => {
          const race = entity.race as keyof typeof cellsByRace || 'neutral';
          cellsByRace[race].push({
            patch: patch.version,
            patchDate: patch.date,
            entityId,
            entity,
            race
          });
        });

        // Calculate positions for each race, left to right
        let xOffset = 0;
        ['terran', 'zerg', 'protoss'].forEach(race => {
          const raceCells = cellsByRace[race as keyof typeof cellsByRace];
          raceCells.forEach((cell: any, index: number) => {
            allCells.push({
              ...cell,
              x: xOffset + index * cellSize,
              y: yScale(patch.version)!
            });
          });
          xOffset += raceCells.length * cellSize;
        });
      });
    } else {
      // Full grid view: show all positions for units in their race columns
      patches.forEach(patch => {
        patch.entities.forEach((entity, entityId) => {
          if (xScale(entityId) !== undefined) {
            allCells.push({
              patch: patch.version,
              patchDate: patch.date,
              entityId,
              entity,
              x: xScale(entityId)!,
              y: yScale(patch.version)!
            });
          }
        });
      });
    }

    // Render all cells (units, upgrades, buildings)
    const cells = g.append('g')
      .selectAll('g')
      .data(allCells)
      .enter()
      .append('g')
      .attr('transform', d => `translate(${d.x},${d.y})`);

    // Add images for units, or colored boxes for upgrades/buildings
    cells.each(function(d) {
      const cell = d3.select(this);

      if (d.entity.type === 'unit') {
        // Render unit with image
        cell.append('image')
          .attr('x', cellPadding)
          .attr('y', cellPadding)
          .attr('width', cellSize - cellPadding * 2)
          .attr('height', cellSize - cellPadding * 2)
          .attr('href', `/assets/units/${d.entityId}.png`)
          .attr('preserveAspectRatio', 'xMidYMid meet')
          .style('cursor', 'pointer')
          .on('error', function() {
            d3.select(this).attr('href', '/assets/units/placeholder.svg');
          });
      } else {
        // Render upgrade/building as colored box with icon/text
        const raceColor = d.race === 'terran' ? '#4a9eff' :
                         d.race === 'zerg' ? '#c874e9' :
                         d.race === 'protoss' ? '#ffd700' : '#888';

        cell.append('rect')
          .attr('x', cellPadding)
          .attr('y', cellPadding)
          .attr('width', cellSize - cellPadding * 2)
          .attr('height', cellSize - cellPadding * 2)
          .attr('fill', raceColor)
          .attr('fill-opacity', 0.3)
          .attr('stroke', raceColor)
          .attr('stroke-width', 2)
          .attr('rx', 4)
          .style('cursor', 'pointer');

        // Add first letter of entity name as icon
        const entityName = d.entity.name || d.entityId.split('-').pop() || '?';
        cell.append('text')
          .attr('x', cellSize / 2)
          .attr('y', cellSize / 2)
          .attr('text-anchor', 'middle')
          .attr('dominant-baseline', 'central')
          .attr('fill', raceColor)
          .attr('font-size', 20)
          .attr('font-weight', 'bold')
          .text(entityName.charAt(0).toUpperCase());
      }

      // Add hover behavior for all cells
      cell.style('cursor', 'pointer')
        .on('mouseenter', function(event) {
          const [x, y] = d3.pointer(event, document.body);
          setTooltip({
            x,
            y,
            unit: units.get(d.entityId)?.name || d.entity.name || d.entityId,
            changes: d.entity.changes,
            visible: true
          });
        })
        .on('mouseleave', () => {
          setTooltip(prev => ({ ...prev, visible: false }));
        });
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