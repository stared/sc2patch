import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ProcessedPatchData, ViewMode, Unit } from '../types';

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

    const margin = { top: 80, right: 20, bottom: 20, left: 120 };
    const cellSize = 54;
    const cellPadding = 3;

    // Calculate max entities per race across all patches for column widths
    const maxEntitiesPerRace = { terran: 0, zerg: 0, protoss: 0, neutral: 0 };

    patches.forEach(patch => {
      const countsPerRace = { terran: 0, zerg: 0, protoss: 0, neutral: 0 };
      patch.entities.forEach((entity) => {
        const race = (entity.race || 'neutral') as keyof typeof countsPerRace;
        countsPerRace[race]++;
      });

      Object.keys(maxEntitiesPerRace).forEach(race => {
        const r = race as keyof typeof maxEntitiesPerRace;
        maxEntitiesPerRace[r] = Math.max(
          maxEntitiesPerRace[r],
          countsPerRace[r]
        );
      });
    });

    // Define fixed column widths (minimum 3 cells per column)
    const columnWidths = {
      terran: Math.max(maxEntitiesPerRace.terran, 3) * cellSize,
      zerg: Math.max(maxEntitiesPerRace.zerg, 3) * cellSize,
      protoss: Math.max(maxEntitiesPerRace.protoss, 3) * cellSize,
      neutral: Math.max(maxEntitiesPerRace.neutral, 3) * cellSize
    };

    // Calculate column x positions
    const columnPositions = {
      terran: 0,
      zerg: columnWidths.terran,
      protoss: columnWidths.terran + columnWidths.zerg,
      neutral: columnWidths.terran + columnWidths.zerg + columnWidths.protoss
    };

    const totalWidth = columnWidths.terran + columnWidths.zerg + columnWidths.protoss + columnWidths.neutral;
    const width = margin.left + margin.right + totalWidth;
    const height = margin.top + margin.bottom + patches.length * cellSize;

    svg.attr('width', width).attr('height', height);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    // Create y scale for patches
    const yScale = d3.scaleBand()
      .domain(patches.map(p => p.version))
      .range([0, patches.length * cellSize])
      .padding(0);

    // Add race headers at fixed column positions
    const raceHeaders = [
      { race: 'terran', color: '#4a9eff' },
      { race: 'zerg', color: '#c874e9' },
      { race: 'protoss', color: '#ffd700' },
      { race: 'neutral', color: '#888' }
    ];

    raceHeaders.forEach(({ race, color }) => {
      const raceKey = race as keyof typeof columnPositions;
      const xPos = columnPositions[raceKey];
      const width = columnWidths[raceKey];

      g.append('text')
        .attr('x', xPos + width / 2)
        .attr('y', -40)
        .attr('text-anchor', 'middle')
        .attr('fill', color)
        .attr('font-size', 16)
        .attr('font-weight', 'bold')
        .text(race.charAt(0).toUpperCase() + race.slice(1));
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

    // Collect all cells positioned in fixed race columns
    const allCells: any[] = [];

    patches.forEach(patch => {
      const cellsByRace = { terran: [], zerg: [], protoss: [], neutral: [] } as any;

      // Group all entities by race
      patch.entities.forEach((entity, entityId) => {
        const race = (entity.race || 'neutral') as keyof typeof cellsByRace;
        cellsByRace[race].push({
          patch: patch.version,
          patchDate: patch.date,
          entityId,
          entity,
          race
        });
      });

      // Position entities in their fixed race columns
      (['terran', 'zerg', 'protoss', 'neutral'] as const).forEach(race => {
        const raceCells = cellsByRace[race];
        const columnXStart = columnPositions[race];

        raceCells.forEach((cell: any, index: number) => {
          allCells.push({
            ...cell,
            x: columnXStart + index * cellSize,
            y: yScale(patch.version)!
          });
        });
      });
    });

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

  }, [patches, units]);

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