// SPDX-License-Identifier: AGPL-3.0-or-later
import { CtaBand, FaqList, FeatureCard, Hero, Section, SiteFooter, SiteHeader } from '@zephyrex/marketing';
import type { ReactElement } from 'react';
import { CLOSING, COMPARE, FAQS, FOOTER, HERO, NAV, PLANNED, START } from '~/content/marketing';
import { APP_NAME } from '~/zephyrex.config';

/** What the wiki will be, for a visitor. Nothing is built yet, so every feature reads as planned. */
export function Landing(): ReactElement {
  return (
    <div className='flex min-h-svh w-full min-w-0 flex-col'>
      <SiteHeader brand={APP_NAME} nav={NAV} cta={START} />
      <main className='mx-auto w-full min-w-0 max-w-5xl space-y-20 px-4'>
        <Hero title={HERO.title} lead={HERO.lead} primary={START} secondary={{ label: 'Questions', href: '#faq' }} />
        <Section id='planned' title='What it will do' eyebrow='Planned'>
          <div className='grid gap-4 sm:grid-cols-2'>
            {PLANNED.map((feature) => (
              <FeatureCard key={feature.id} feature={feature} />
            ))}
          </div>
        </Section>
        <Section id='compare' title='Coming from Kanka or World Anvil?' eyebrow='How it compares'>
          <div className='overflow-x-auto rounded-xl border'>
            <table className='w-full min-w-[32rem] text-left text-sm'>
              <thead className='bg-muted/50'>
                <tr>
                  <th scope='col' className='p-3 font-semibold'>
                    <span className='sr-only'>Point</span>
                  </th>
                  <th scope='col' className='p-3 font-semibold'>
                    {APP_NAME}
                  </th>
                  <th scope='col' className='p-3 font-semibold'>
                    Kanka and World Anvil
                  </th>
                </tr>
              </thead>
              <tbody className='divide-y'>
                {COMPARE.map((row) => (
                  <tr key={row.point}>
                    <th scope='row' className='p-3 font-medium'>
                      {row.point}
                    </th>
                    <td className='p-3'>{row.us}</td>
                    <td className='p-3 text-muted-foreground'>{row.them}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
        <Section id='faq' title='Questions' eyebrow='FAQ'>
          <FaqList faqs={FAQS} />
        </Section>
        <CtaBand title={CLOSING.title} body={CLOSING.body} action={START} />
        <SiteFooter columns={FOOTER} note={`${APP_NAME} is open source under the AGPL.`} />
      </main>
    </div>
  );
}
